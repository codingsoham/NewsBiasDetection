"""Persist model predictions and conservative title-based cross-source story clusters.
Supports both CLI batch mode and real-time on-demand refresh for the API and app.
Integrates major Indian national and politics feeds including Google News India aggregator.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import signal
import sqlite3
import sys
import threading
import time
from urllib.parse import urlsplit

import feedparser
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import DB, ensure, predict_batch
from ml.collect_indian import clean_html, entry_date, fetch, is_english, normalise_url, now

STOPWORDS = {
    'about', 'after', 'again', 'against', 'among', 'and', 'are', 'been', 'before', 'but',
    'for', 'from', 'have', 'into', 'its', 'more', 'news', 'over', 'that', 'the', 'their',
    'this', 'was', 'were', 'with'
}

EXPANDED_FEEDS: list[tuple[str, str]] = [
    ('Google News National', 'https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News Politics', 'https://news.google.com/rss/headlines/section/topic/POLITICS?hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News 24h Politics', 'https://news.google.com/rss/search?q=India+politics+when:24h&hl=en-IN&gl=IN&ceid=IN:en'),
    ('The Hindu', 'https://www.thehindu.com/news/national/feeder/default.rss'),
    ('Indian Express Politics', 'https://indianexpress.com/section/politics/feed/'),
    ('Indian Express Pulse', 'https://indianexpress.com/section/political-pulse/feed/'),
    ('Indian Express India', 'https://indianexpress.com/section/india/feed/'),
    ('NDTV India', 'https://feeds.feedburner.com/ndtvnews-india-news'),
    ('Times of India India', 'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms'),
    ('Hindustan Times', 'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml'),
    ('ThePrint Politics', 'https://theprint.in/category/politics/feed/'),
    ('India Today National', 'https://www.indiatoday.in/rss/1206578'),
    ('India Today Politics', 'https://www.indiatoday.in/rss/1206514'),
    ('LiveMint Politics', 'https://www.livemint.com/rss/politics'),
    ('Google News Deccan Herald', 'https://news.google.com/rss/search?q=site:deccanherald.com+politics&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News Swarajya', 'https://news.google.com/rss/search?q=site:swarajyamag.com&hl=en-IN&gl=IN&ceid=IN:en'),
    ('OpIndia', 'https://www.opindia.com/feed/'),
    ('Google News OpIndia', 'https://news.google.com/rss/search?q=site:opindia.com&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Organiser', 'https://organiser.org/feed/'),
    ('Google News Organiser', 'https://news.google.com/rss/search?q=site:organiser.org&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News Firstpost', 'https://news.google.com/rss/search?q=site:firstpost.com&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News The Wire', 'https://news.google.com/rss/search?q=site:thewire.in&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News Scroll', 'https://news.google.com/rss/search?q=site:scroll.in&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News The Quint', 'https://news.google.com/rss/search?q=site:thequint.com+india&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News Free Press Journal', 'https://news.google.com/rss/search?q=site:freepressjournal.in+india&hl=en-IN&gl=IN&ceid=IN:en'),
]


def keywords(row) -> set[str]:
    try:
        from backend.text_cleaner import build_clean_evaluation_text
    except ImportError:
        from text_cleaner import build_clean_evaluation_text
    text = build_clean_evaluation_text(row['title'], row['snippet'])
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", text) if w.lower() not in STOPWORDS}


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('all-MiniLM-L6-v2')


def fetch_live_rss(c: sqlite3.Connection) -> int:
    """Fetch all configured Indian news feeds in parallel without blocking."""
    def _fetch_one(target: tuple[str, str]):
        name, feed_url = target
        try:
            raw = fetch(feed_url, timeout=12, attempts=2)
            return name, feed_url, raw, None
        except Exception as err:
            return name, feed_url, None, err

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(EXPANDED_FEEDS), 12)) as ex:
        results = list(ex.map(_fetch_one, EXPANDED_FEEDS))

    existing_urls = {r[0] for r in c.execute("SELECT normalized_url FROM articles").fetchall()}
    existing_hashes = {r[0] for r in c.execute("SELECT content_hash FROM articles").fetchall()}

    to_insert: list[tuple] = []
    current_time = now()

    for feed_name, feed_url, raw_bytes, err in results:
        if err or not raw_bytes:
            logging.warning("Feed fetch warning [%s]: %s", feed_url, err)
            continue
        try:
            parsed = feedparser.parse(raw_bytes)
        except Exception as parse_err:
            logging.warning("Feed parse warning [%s]: %s", feed_url, parse_err)
            continue

        for entry in parsed.entries:
            raw_url = str(entry.get("link", ""))
            norm_url = normalise_url(raw_url)
            if not norm_url or norm_url in existing_urls:
                continue

            try:
                from backend.text_cleaner import clean_snippet, strip_publisher_watermarks, unescape_text
            except ImportError:
                from text_cleaner import clean_snippet, strip_publisher_watermarks, unescape_text

            raw_title = clean_html(str(entry.get("title", "")))
            raw_snippet = clean_html(str(entry.get("summary", entry.get("description", ""))))

            entry_source = entry.get("source", {}).get("title")
            title = strip_publisher_watermarks(unescape_text(raw_title))
            if "Google News" in feed_name and " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                title = strip_publisher_watermarks(unescape_text(parts[0].strip()))
                if not entry_source:
                    entry_source = parts[1].strip()

            final_source = entry_source or feed_name.split()[0]
            if not final_source or final_source.lower() in ("news", "unknown", ""):
                final_source = "National News"

            snippet = clean_snippet(title, raw_snippet)

            if len(title) < 15 or not is_english(f"{title} {snippet}"):
                continue

            try:
                from backend.indian_filter import classify_indian_news
            except ImportError:
                from indian_filter import classify_indian_news

            is_indian, _ = classify_indian_news(title, snippet)
            if not is_indian:
                continue

            content_hash = hashlib.sha256(f"{title}\n{snippet}".encode("utf-8")).hexdigest()
            if content_hash in existing_hashes:
                continue

            existing_urls.add(norm_url)
            existing_hashes.add(content_hash)
            pub_date = entry_date(entry)

            to_insert.append((
                final_source, raw_url, norm_url, title, snippet, None, content_hash, pub_date, current_time
            ))

    if to_insert:
        c.executemany(
            """INSERT INTO articles (source, url, normalized_url, title, snippet, text, content_hash, published_at, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            to_insert
        )
        c.commit()

    return len(to_insert)


def predict_pending(c: sqlite3.Connection) -> int:
    """Predict bias for any articles lacking predictions using fast batched inference with pure content evaluation."""
    unpredicted = c.execute(
        "SELECT id, source, title, snippet FROM articles WHERE id NOT IN (SELECT article_id FROM predictions) ORDER BY id"
    ).fetchall()
    if not unpredicted:
        return 0

    try:
        from backend.text_cleaner import build_clean_evaluation_text
    except ImportError:
        from text_cleaner import build_clean_evaluation_text

    texts = [build_clean_evaluation_text(r['title'], r['snippet']) for r in unpredicted]
    sources = [r['source'] for r in unpredicted]
    predictions = predict_batch(texts, sources=sources, batch_size=64)

    records = [
        (
            r['id'],
            p['LEFT'],
            p['CENTER'],
            p['RIGHT'],
            int(max(p.values()) < 0.45),
            'models/best/best'
        )
        for r, p in zip(unpredicted, predictions)
    ]

    c.executemany(
        """INSERT OR REPLACE INTO predictions (article_id, p_left, p_center, p_right, low_confidence, model_path)
           VALUES (?, ?, ?, ?, ?, ?)""",
        records
    )
    c.commit()
    return len(records)


def cluster_stories(c: sqlite3.Connection, threshold: float = 0.68, min_keyword_overlap: int = 1, recent_only: bool = True) -> tuple[int, int]:
    """Group articles into multi-source stories within a 72-hour window."""
    if recent_only:
        rows = c.execute(
            """SELECT id, title, snippet, source, published_at, fetched_at FROM articles
               ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT 900"""
        ).fetchall()
        rows = sorted(rows, key=lambda r: r['id'])
    else:
        rows = c.execute("SELECT id, title, snippet, source, published_at, fetched_at FROM articles ORDER BY id").fetchall()

    try:
        from backend.indian_filter import classify_indian_news
    except ImportError:
        from indian_filter import classify_indian_news

    # Filter candidates strictly to Indian news before clustering
    rows = [r for r in rows if classify_indian_news(r['title'], r['snippet'])[0]]

    if not rows:
        return 0, 0

    model = _embedding_model()
    texts = [(r['title'] or '') + ' ' + (r['snippet'] or '') for r in rows]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    groups: list[dict] = []
    for r, v in zip(rows, vectors):
        r_time_str = r['published_at'] or r['fetched_at'] or ''
        def within(g):
            g_time_str = g['rows'][0]['published_at'] or g['rows'][0]['fetched_at'] or ''
            try:
                t1 = datetime.fromisoformat(r_time_str.replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(g_time_str.replace('Z', '+00:00'))
                return abs((t1 - t2).total_seconds()) <= 72 * 3600
            except ValueError:
                return True

        match = next(
            (
                g for g in groups
                if r['source'].lower() not in {s.lower() for s in g['sources']}
                and within(g)
                and float(np.dot(v, g['vector'])) >= threshold
                and len(keywords(r) & g['keywords']) >= min_keyword_overlap
            ),
            None
        )
        if match:
            match['rows'].append(r)
            match['sources'].add(r['source'])
            match['keywords'] |= keywords(r)
            match['vector'] = (match['vector'] + v) / np.linalg.norm(match['vector'] + v)
        else:
            groups.append({'rows': [r], 'sources': {r['source']}, 'keywords': keywords(r), 'vector': v})

    c.execute("DELETE FROM story_articles")
    c.execute("DELETE FROM stories")

    multi_groups = [g for g in groups if len(g['sources']) >= 2]
    # Prioritize multi-source stories like Ground News, fallback to single source if multi count is small
    target_groups = multi_groups
    if len(target_groups) < 15:
        single_groups = [g for g in groups if len(g['sources']) == 1]
        target_groups = multi_groups + single_groups[:(25 - len(target_groups))]

    total_stories = 0
    total_links = 0
    for g in target_groups:
        cur = c.execute("INSERT INTO stories (title) VALUES (?)", (g['rows'][0]['title'],))
        story_id = cur.lastrowid
        links = [(story_id, r['id']) for r in g['rows']]
        c.executemany("INSERT INTO story_articles (story_id, article_id) VALUES (?, ?)", links)
        total_stories += 1
        total_links += len(links)

    c.commit()
    return total_stories, total_links


def refresh_realtime_news(
    c: sqlite3.Connection | None = None,
    force: bool = False,
    throttle_seconds: int = 15,
    threshold: float = 0.68
) -> dict:
    """Check live RSS feeds, run predictions on new items, and update story clusters.
    Uses a 90-second throttle to keep feeds fresh on pull-to-refresh while avoiding publisher spam.
    """
    close_when_done = False
    if c is None:
        DB.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(DB, timeout=30.0)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA busy_timeout=30000;")
        close_when_done = True

    ensure(c)

    row = c.execute("SELECT value FROM app_meta WHERE key = 'last_refresh_timestamp'").fetchone()
    last_ts = float(row['value']) if row else 0.0
    now_ts = time.time()
    elapsed = now_ts - last_ts

    if not force and elapsed < throttle_seconds:
        if close_when_done:
            c.close()
        return {
            "status": "throttled",
            "message": f"Refreshed {int(elapsed)}s ago (throttle: {throttle_seconds}s)",
            "elapsed_seconds": round(elapsed, 1),
        }

    try:
        new_articles = fetch_live_rss(c)
        new_predictions = predict_pending(c)
        stories_count, links_count = cluster_stories(c, threshold=threshold)

        c.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('last_refresh_timestamp', ?)",
            (str(now_ts),)
        )
        c.commit()

        res = {
            "status": "refreshed",
            "new_articles": new_articles,
            "new_predictions": new_predictions,
            "stories": stories_count,
            "story_links": links_count,
            "refreshed_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as exc:
        logging.error("Realtime refresh error: %s", exc)
        res = {"status": "error", "error": str(exc)}
    finally:
        if close_when_done:
            c.close()

    return res


_daemon_thread: threading.Thread | None = None
_daemon_stop_event = threading.Event()
_daemon_status: dict = {
    "running": False,
    "last_run_time": None,
    "last_result": None,
    "run_count": 0,
    "interval_seconds": 1800,
}


def get_daemon_status() -> dict:
    return dict(_daemon_status)


def run_ingestion_daemon(
    interval_seconds: int = 1800,
    stop_event: threading.Event | None = None,
    initial_delay: int = 5
):
    """Background daemon loop that fetches RSS feeds, predicts bias, and clusters stories every interval_seconds (default 30 mins)."""
    global _daemon_status
    _daemon_status["running"] = True
    _daemon_status["interval_seconds"] = interval_seconds
    logging.info("Starting background ingestion daemon (interval: %ds, initial delay: %ds)...", interval_seconds, initial_delay)

    # Initial delay allows API server to bind and be fully ready before background ingestion pass
    if initial_delay > 0:
        slept = 0
        while slept < initial_delay:
            if stop_event is not None and stop_event.is_set():
                _daemon_status["running"] = False
                return
            time.sleep(1)
            slept += 1

    while stop_event is None or not stop_event.is_set():
        try:
            logging.info("Ingestion daemon: starting 30-min scheduled news sync...")
            res = refresh_realtime_news(force=True)
            _daemon_status["last_run_time"] = datetime.now(timezone.utc).isoformat()
            _daemon_status["last_result"] = res
            _daemon_status["run_count"] += 1
            logging.info("Ingestion daemon: sync complete -> %s", res)
        except Exception as exc:
            logging.error("Ingestion daemon error: %s", exc)
            _daemon_status["last_result"] = {"status": "error", "error": str(exc)}

        # Wait in 1-second slices so shutdown is instant
        slept = 0
        while slept < interval_seconds:
            if stop_event is not None and stop_event.is_set():
                break
            time.sleep(1)
            slept += 1

    _daemon_status["running"] = False
    logging.info("Background ingestion daemon stopped.")


def start_daemon(interval_seconds: int = 1800, initial_delay: int = 5):
    """Start background ingestion thread if not already running."""
    global _daemon_thread, _daemon_stop_event
    if _daemon_thread is not None and _daemon_thread.is_alive():
        logging.info("Ingestion daemon is already running.")
        return
    _daemon_stop_event.clear()
    _daemon_thread = threading.Thread(
        target=run_ingestion_daemon,
        args=(interval_seconds, _daemon_stop_event, initial_delay),
        daemon=True,
        name="NewsIngestionDaemon"
    )
    _daemon_thread.start()
    logging.info("Background ingestion daemon thread started.")


def stop_daemon():
    """Signal ingestion daemon to stop and wait for completion."""
    global _daemon_thread, _daemon_stop_event
    if _daemon_thread is not None and _daemon_thread.is_alive():
        logging.info("Stopping background ingestion daemon...")
        _daemon_stop_event.set()
        _daemon_thread.join(timeout=5)
        logging.info("Background ingestion daemon joined.")


def main(
    threshold: float = 0.68,
    refresh: bool = False,
    min_keyword_overlap: int = 1,
    refresh_rss: bool = False,
    daemon: bool = False,
    interval: int = 1800,
    run_once: bool = False
):
    if daemon:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s"
        )
        logging.info("Starting standalone NewsBias Ingestion Daemon (interval=%ds)...", interval)
        stop_event = threading.Event()

        def _signal_handler(signum, frame):
            sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
            logging.info("Received signal %s (%d), shutting down cleanly...", sig_name, signum)
            stop_event.set()

        try:
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
        except (ValueError, AttributeError):
            pass

        run_ingestion_daemon(interval_seconds=interval, stop_event=stop_event, initial_delay=0)
        logging.info("Daemon process exited.")
        return

    if run_once:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
        logging.info("Executing single on-demand live ingestion pass...")
        res = refresh_realtime_news(force=True, threshold=threshold)
        print(json.dumps(res, indent=2))
        return

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    ensure(c)

    if refresh:
        c.execute("DELETE FROM predictions")
        c.commit()

    if refresh_rss:
        inserted = fetch_live_rss(c)
        print(f"Fetched RSS: {inserted} new articles inserted.")

    predicted = predict_pending(c)
    if predicted:
        print(f"Predicted {predicted} articles.")

    stories_count, links_count = cluster_stories(c, threshold=threshold, min_keyword_overlap=min_keyword_overlap, recent_only=False)
    print(f"predictions {c.execute('SELECT count(*) FROM predictions').fetchone()[0]} stories {stories_count} (links {links_count})")
    c.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description="NewsBias India Live News Ingestion & Clustering Pipeline")
    p.add_argument('--threshold', type=float, default=0.68, help="Semantic clustering similarity threshold (default: 0.68)")
    p.add_argument('--min-keyword-overlap', type=int, default=1, help="Minimum named-entity / keyword token overlap (default: 1)")
    p.add_argument('--refresh-predictions', action='store_true', help="Clear existing predictions table and re-run model")
    p.add_argument('--refresh-rss', action='store_true', help="Collect current configured RSS items before materializing")
    p.add_argument('--daemon', action='store_true', help="Run as a continuous standalone background ingestion daemon")
    p.add_argument('--interval', type=int, default=1800, help="Daemon cycle interval in seconds (default: 1800 / 30 mins)")
    p.add_argument('--run-once', action='store_true', help="Execute an immediate single-pass ingestion and print status")
    a = p.parse_args()
    main(
        threshold=a.threshold,
        refresh=a.refresh_predictions,
        min_keyword_overlap=a.min_keyword_overlap,
        refresh_rss=a.refresh_rss,
        daemon=a.daemon,
        interval=a.interval,
        run_once=a.run_once
    )
