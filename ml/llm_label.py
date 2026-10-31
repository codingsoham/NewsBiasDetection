"""Double-pass LLM labelling for locally stored Phase 1 articles.

The LLM receives article text solely for research/training labels. Text is never
written to an API response by this program and is not served by the backend.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from labeling_common import connect, ensure_labeling_schema, load_dotenv, normalise_label, utc_now

GUIDELINE_PATH = Path(__file__).with_name("guideline.md")
PROMPTS = {
    "v1": "First distinguish the journalist's framing from claims made by quoted people. A politician criticising a government, or a government criticising an opponent, is attribution—not the outlet's stance. Use LEFT or RIGHT only for clear authorial evaluative framing. Prefer CENTER whenever this is not clear.",
    "v2": "Independently apply an attribution check before deciding. Do not infer a slant from which party is discussed, a partisan quote, or an official statement. Label LEFT or RIGHT only where the article's own headline, wording, emphasis, or conclusion clearly endorses that framing; otherwise choose CENTER.",
}


def extract_json(content: str) -> dict:
    if not isinstance(content, str):
        raise ValueError("LLM response did not contain text content")
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain a JSON object")
    value = json.loads(match.group(0))
    label = normalise_label(value["label"])
    rationale = str(value["rationale"]).strip()
    confidence = float(value["confidence"])
    if not rationale or not 0 <= confidence <= 1:
        raise ValueError("invalid rationale or confidence")
    return {"label": label, "rationale": rationale[:1000], "confidence": confidence}


def label_article(article: dict, prompt_version: str) -> tuple[dict, str]:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key or api_key == "replace_me":
        raise RuntimeError("LLM_API_KEY is missing. Add it to .env (see .env.example).")
    guideline = GUIDELINE_PATH.read_text(encoding="utf-8")
    system = f"""You are a careful annotation assistant. Follow these definitions exactly:\n\n{guideline}\n\n{PROMPTS[prompt_version]}\n\nCritical rule: quoted or attributed partisan claims are evidence of the speaker's view, not of the article's framing. Mere coverage of government, BJP, Congress, opposition, religion, or elections is not enough for LEFT or RIGHT. Do not use an outlet's reputation. Do not guess.\n\nReturn only JSON with keys label, rationale, confidence. label must be exactly LEFT, CENTER, RIGHT, or NOT_POLITICAL. confidence is a number from 0 to 1. The rationale must state the article-owned wording or structure that supports the decision; if there is none, say it is neutral attribution. The rationale must be one sentence."""
    article_text = article["text"] or ""
    # Free providers can be slow on long articles. Preserve opening and closing
    # framing while bounding each request to a practical review-sized payload.
    if len(article_text) > 8_000:
        article_text = article_text[:4_000] + "\n[...middle omitted...]\n" + article_text[-4_000:]
    body = {
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "temperature": 0,
        "reasoning_effort": "none",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Title: {article['title'] or ''}\nSnippet: {article['snippet'] or ''}\nArticle:\n{article_text}"},
        ],
    }
    request = urllib.request.Request(
        os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions"),
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode("utf-8")
            payload = json.loads(raw)
            content = payload["choices"][0]["message"].get("content")
            return extract_json(content), raw
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"LLM did not return a valid label after retries: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create double-pass silver labels.")
    parser.add_argument("--db", help="SQLite database path")
    parser.add_argument("--limit", type=int, help="maximum eligible articles")
    parser.add_argument("--force", action="store_true", help="replace prior LLM annotations")
    parser.add_argument("--delay", type=float, default=0.4, help="seconds between API calls")
    args = parser.parse_args()
    load_dotenv()
    db = connect(args.db)
    ensure_labeling_schema(db)
    try:
        # Headlines/snippets without body text must also be labelled: the
        # guideline specifically routes insufficient substance to NOT_POLITICAL.
        query = "SELECT id, title, snippet, text FROM articles WHERE COALESCE(TRIM(text), '') != '' OR COALESCE(TRIM(title), '') != '' OR COALESCE(TRIM(snippet), '') != ''"
        if not args.force:
            query += " AND id NOT IN (SELECT article_id FROM llm_annotations GROUP BY article_id HAVING COUNT(*) >= 2)"
        query += " ORDER BY id"
        if args.limit:
            query += f" LIMIT {int(args.limit)}"
        articles = db.execute(query).fetchall()
    except Exception as error:
        raise SystemExit("Expected a Phase 1 articles table with id, title, snippet, and text columns. " + str(error))
    print(f"Eligible articles: {len(articles)}")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    for index, article in enumerate(articles, start=1):
        if args.force:
            # A forced re-run must never combine a fresh pass with a stale pass
            # from an earlier prompt/model version.
            db.execute("DELETE FROM llm_annotations WHERE article_id = ?", (article["id"],))
            db.execute("DELETE FROM silver_labels WHERE article_id = ?", (article["id"],))
            db.commit()
        results = []
        for version in PROMPTS:
            try:
                result, raw = label_article(dict(article), version)
                results.append(result)
                db.execute("INSERT OR REPLACE INTO llm_annotations (article_id,prompt_version,label,rationale,confidence,model,raw_response,created_at) VALUES (?,?,?,?,?,?,?,?)", (article["id"], version, result["label"], result["rationale"], result["confidence"], model, raw, utc_now()))
                db.commit()
            except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, json.JSONDecodeError, TypeError) as error:
                print(f"[{index}/{len(articles)}] article {article['id']} {version}: FAILED: {error}")
                break
            time.sleep(args.delay)
        if len(results) == 2 and results[0]["label"] == results[1]["label"]:
            db.execute("INSERT OR REPLACE INTO silver_labels (article_id,label,confidence,prompt_versions,created_at) VALUES (?,?,?,?,?)", (article["id"], results[0]["label"], (results[0]["confidence"] + results[1]["confidence"]) / 2, ",".join(PROMPTS), utc_now()))
        elif len(results) == 2:
            db.execute("DELETE FROM silver_labels WHERE article_id = ?", (article["id"],))
        db.commit()
        print(f"[{index}/{len(articles)}] article {article['id']}: " + ("SILVER" if len(results) == 2 and results[0]['label'] == results[1]['label'] else "REVIEW"))
    counts = db.execute("SELECT label, COUNT(*) AS n FROM silver_labels GROUP BY label ORDER BY label").fetchall()
    print("Silver labels:", dict((row["label"], row["n"]) for row in counts))


if __name__ == "__main__":
    main()
