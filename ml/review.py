"""Local, keyboard-driven review of a stratified Phase 2 sample."""
from __future__ import annotations

import argparse
import html
import random
import sqlite3
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from labeling_common import LABELS, connect, ensure_labeling_schema, load_dotenv, utc_now


def _stratified_pick(rows: list[sqlite3.Row], limit: int, seed: int) -> list[sqlite3.Row]:
    """Round-robin through source/label strata, with deterministic shuffling."""
    groups: dict[tuple[str, str], deque] = defaultdict(deque)
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    for row in shuffled:
        groups[(row["source"], row["suggested_label"])].append(row)
    selected: list[sqlite3.Row] = []
    while groups and len(selected) < limit:
        for key in list(groups):
            bucket = groups[key]
            if bucket:
                selected.append(bucket.popleft())
                if len(selected) >= limit:
                    break
            if not bucket:
                del groups[key]
    return selected


def prepare_queue(db: sqlite3.Connection, sample_size: int) -> int:
    """Stratify by source/prediction and reserve half the review budget for disagreements."""
    db.execute("DELETE FROM review_queue WHERE completed_at IS NULL")
    rows = db.execute(
        """
        WITH paired AS (
          SELECT a.id, COALESCE(a.source, 'Unknown') AS source,
                 x.label AS first_label, y.label AS second_label,
                 CASE WHEN x.label = y.label THEN x.label ELSE x.label END AS suggested_label
          FROM articles a
          JOIN llm_annotations x ON x.article_id=a.id AND x.prompt_version='v1'
          JOIN llm_annotations y ON y.article_id=a.id AND y.prompt_version='v2'
        ) SELECT * FROM paired ORDER BY id
        """
    ).fetchall()
    disagreements = [row for row in rows if row["first_label"] != row["second_label"]]
    agreements = [row for row in rows if row["first_label"] == row["second_label"]]
    disagreement_quota = min(len(disagreements), (sample_size + 1) // 2)
    selected = _stratified_pick(disagreements, disagreement_quota, seed=41)
    selected.extend(_stratified_pick(agreements, sample_size - len(selected), seed=73))
    for row in selected:
        disagreement = row["first_label"] != row["second_label"]
        db.execute("INSERT INTO review_queue (article_id,suggested_label,reason,selected_at) VALUES (?,?,?,?)", (row["id"], row["suggested_label"], "llm_disagreement" if disagreement else "stratified_silver_audit", utc_now()))
    db.commit()
    return len(selected)


def create_handler(db_path: str, reviewer_id: str):
    class ReviewHandler(BaseHTTPRequestHandler):
        def send_html(self, status: int, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):  # noqa: N802
            db = connect(db_path)
            ensure_labeling_schema(db)
            if self.path == "/":
                article = db.execute(
                    """SELECT a.id,a.title,a.snippet,a.text,a.url,q.suggested_label,q.reason,
                       (SELECT label FROM llm_annotations WHERE article_id=a.id AND prompt_version='v1') AS v1,
                       (SELECT label FROM llm_annotations WHERE article_id=a.id AND prompt_version='v2') AS v2,
                       (SELECT COUNT(*) FROM review_queue WHERE completed_at IS NULL) AS remaining
                       FROM review_queue q JOIN articles a ON a.id=q.article_id
                       WHERE q.completed_at IS NULL ORDER BY q.selected_at,a.id LIMIT 1"""
                ).fetchone()
                if not article:
                    self.send_html(200, "<h1>Review complete</h1><p>No queued articles remain.</p>")
                    return
                choices = "".join(f'<button name="label" value="{label}">[{label[0]}] {label}</button>' for label in LABELS)
                article_text = (article["text"] or article["snippet"] or "(no article text available)")[:16_000]
                self.send_html(200, f"""<!doctype html><title>Label review</title><style>body{{font:18px system-ui;max-width:900px;margin:40px auto;line-height:1.5}}button{{padding:12px;margin:6px;font-size:16px}}.meta{{color:#555}}.article{{white-space:pre-wrap;background:#f6f6f6;padding:18px}}</style>
                <h1>Article {article['id']} <small class=meta>({article['remaining']} left)</small></h1><p class=meta>Suggested: <b>{html.escape(article['suggested_label'])}</b>; pass 1: {html.escape(article['v1'])}; pass 2: {html.escape(article['v2'])}; selected: {html.escape(article['reason'])}</p>
                <h2>{html.escape(article['title'] or '(untitled)')}</h2><p>{html.escape(article['snippet'] or '(no snippet)')}</p><p class="article">{html.escape(article_text)}</p><p><a href="{html.escape(article['url'] or '#', quote=True)}" target="_blank" rel="noopener">Open original article</a></p>
                <form method="post" action="/review"><input type="hidden" name="article_id" value="{article['id']}">{choices}</form>
                <script>document.addEventListener('keydown',e=>{{const m={{l:'LEFT',c:'CENTER',r:'RIGHT',n:'NOT_POLITICAL'}};if(m[e.key.toLowerCase()]){{document.querySelector(`[value="${{m[e.key.toLowerCase()]}}"]`).click()}}}})</script>""")
            else:
                self.send_html(404, "Not found")

        def do_POST(self):  # noqa: N802
            if self.path != "/review":
                self.send_html(404, "Not found")
                return
            length = int(self.headers.get("Content-Length", "0"))
            values = parse_qs(self.rfile.read(length).decode("utf-8"))
            try:
                article_id, label = int(values["article_id"][0]), values["label"][0]
                if label not in LABELS:
                    raise ValueError("invalid label")
            except (KeyError, ValueError):
                self.send_html(400, "Invalid review")
                return
            db = connect(db_path)
            ensure_labeling_schema(db)
            db.execute("INSERT INTO human_reviews (article_id,reviewer_id,label,reviewed_at) VALUES (?,?,?,?) ON CONFLICT(article_id,reviewer_id) DO UPDATE SET label=excluded.label,reviewed_at=excluded.reviewed_at", (article_id, reviewer_id, label, utc_now()))
            db.execute("UPDATE review_queue SET completed_at=? WHERE article_id=?", (utc_now(), article_id))
            db.commit()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def log_message(self, format, *args):  # keep terminal useful
            return
    return ReviewHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and review a local annotation sample.")
    parser.add_argument("--db", help="SQLite database path")
    parser.add_argument("--prepare", type=int, metavar="N", help="replace the outstanding queue with a stratified N-article sample")
    parser.add_argument("--prepare-only", action="store_true", help="prepare the queue then exit without starting the local review server")
    parser.add_argument("--reviewer", default="reviewer_1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    load_dotenv()
    path = args.db or None
    db = connect(path)
    ensure_labeling_schema(db)
    if args.prepare is not None:
        print(f"Queued {prepare_queue(db, args.prepare)} article(s) for review.")
    if args.prepare_only:
        if args.prepare is None:
            parser.error("--prepare-only requires --prepare N")
        return
    actual_path = db.execute("PRAGMA database_list").fetchone()[2]
    print(f"Reviewing as {args.reviewer} at http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), create_handler(actual_path, args.reviewer)).serve_forever()


if __name__ == "__main__":
    main()
