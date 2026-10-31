"""Polite, idempotent collection of Indian English national/political RSS news."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import logging
import re
import ssl
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.robotparser
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import certifi
try:
    import trafilatura
except ImportError:  # lets --verify-feeds run before optional extraction install completes
    trafilatura = None
try:
    from langdetect import DetectorFactory, LangDetectException, detect
    DetectorFactory.seed = 0
except ImportError:
    detect = None
    LangDetectException = ValueError
USER_AGENT = "NewsBiasDetectionResearch/0.1 (+local academic project; contact: local)"
REQUEST_PAUSE_SECONDS = 1.25

# Each URL is checked by --verify-feeds before collection. Do not assume a feed
# remains available: failures are recorded and do not stop the other publishers.
FEEDS = {
    "The Hindu": ["https://www.thehindu.com/news/national/feeder/default.rss"],
    "Indian Express": ["https://indianexpress.com/section/politics/feed/", "https://indianexpress.com/section/political-pulse/feed/"],
    "NDTV": ["https://feeds.feedburner.com/ndtvnews-india-news"],
    "Times of India": ["https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"],
    "Hindustan Times": ["https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"],
    "ThePrint": ["https://theprint.in/category/politics/feed/"],
    "India Today": ["https://www.indiatoday.in/rss/1206578"],
    "Firstpost": ["https://www.firstpost.com/commonfeeds/v1/mfp/rss/india.xml"],
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalise_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    stable_query = [(k, v) for k, v in query if not k.lower().startswith(("utm_", "fbclid", "gclid"))]
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", urllib.parse.urlencode(stable_query), ""))


def fetch(url: str, timeout: int = 30, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml,application/xml,text/xml,text/html;q=0.9"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context(cafile=certifi.where())) as response:
                if response.status >= 400:
                    raise urllib.error.HTTPError(url, response.status, "HTTP error", response.headers, None)
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"{url}: {last_error}")


def robots_allow(url: str, cache: dict[str, urllib.robotparser.RobotFileParser]) -> bool:
    parsed = urllib.parse.urlsplit(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    if root not in cache:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(root + "/robots.txt")
        try:
            parser.parse(fetch(root + "/robots.txt").decode("utf-8", errors="replace").splitlines())
        except (urllib.error.URLError, OSError, RuntimeError):
            # A failure to retrieve robots is not permission to crawl; skip body extraction.
            return False
        cache[root] = parser
    return cache[root].can_fetch(USER_AGENT, url)


def clean_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def is_english(text: str) -> bool:
    if len(text.strip()) < 30:
        return False
    if detect is None:
        # Conservative fallback used only when langdetect is not installed.
        return sum(char.isascii() and (char.isalpha() or char.isspace()) for char in text) / len(text) > 0.75
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False


def entry_date(entry: object) -> str | None:
    for key in ("published", "updated"):
        value = entry.get(key) if hasattr(entry, "get") else None
        if value:
            try:
                return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                return str(value)
    return None


def ensure_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            normalized_url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            snippet TEXT,
            text TEXT,
            content_hash TEXT,
            published_at TEXT,
            fetched_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash) WHERE content_hash IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            backfill INTEGER NOT NULL,
            feed_url TEXT NOT NULL,
            source TEXT NOT NULL,
            entries_seen INTEGER NOT NULL DEFAULT 0,
            inserted INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            errors TEXT
        );
        """
    )
    db.commit()


class ParagraphText(HTMLParser):
    """Small fallback used only when trafilatura cannot be installed."""
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "nav", "footer", "header", "aside"}:
            self.skip_depth += 1
        if tag in {"p", "h1", "h2", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "nav", "footer", "header", "aside"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def fallback_extract(html: bytes) -> str | None:
    parser = ParagraphText()
    parser.feed(html.decode("utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return text if len(text) >= 200 else None


def body_for(url: str, robots: dict[str, urllib.robotparser.RobotFileParser]) -> str | None:
    if not robots_allow(url, robots):
        logging.info("robots.txt disallows article extraction: %s", url)
        return None
    try:
        if trafilatura is None:
            logging.warning("trafilatura unavailable; using limited HTML-text fallback")
            return fallback_extract(fetch(url))
        downloaded = trafilatura.fetch_url(url, no_ssl=False)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False, favor_precision=True)
        return re.sub(r"\s+", " ", text or "").strip() or None
    except Exception as error:  # extraction failures should never abort an RSS run
        logging.warning("body extraction failed for %s: %s", url, error)
        return None


def collect_feed(db: sqlite3.Connection, source: str, feed_url: str, extract_bodies: bool, backfill: bool) -> dict[str, int | str]:
    run = db.execute("INSERT INTO collection_runs (started_at,backfill,feed_url,source) VALUES (?,?,?,?)", (now(), int(backfill), feed_url, source))
    run_id = run.lastrowid
    stats: dict[str, int | str] = {"seen": 0, "inserted": 0, "skipped": 0, "errors": ""}
    robots: dict[str, urllib.robotparser.RobotFileParser] = {}
    try:
        data = fetch(feed_url)
        parsed = feedparser.parse(data)
        if parsed.bozo and not parsed.entries:
            raise RuntimeError(f"unparseable feed: {parsed.bozo_exception}")
        for entry in parsed.entries:
            stats["seen"] = int(stats["seen"]) + 1
            url = normalise_url(str(entry.get("link", "")))
            title = clean_html(str(entry.get("title", "")))
            snippet = clean_html(str(entry.get("summary", entry.get("description", ""))))
            if not url or not title or not is_english(f"{title} {snippet}"):
                stats["skipped"] = int(stats["skipped"]) + 1
                continue
            if db.execute("SELECT 1 FROM articles WHERE normalized_url=?", (url,)).fetchone():
                stats["skipped"] = int(stats["skipped"]) + 1
                continue
            text = body_for(url, robots) if extract_bodies else None
            payload = text or f"{title}\n{snippet}"
            content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if db.execute("SELECT 1 FROM articles WHERE content_hash=?", (content_hash,)).fetchone():
                stats["skipped"] = int(stats["skipped"]) + 1
                continue
            db.execute("INSERT INTO articles (source,url,normalized_url,title,snippet,text,content_hash,published_at,fetched_at) VALUES (?,?,?,?,?,?,?,?,?)", (source, url, url, title, snippet, text, content_hash, entry_date(entry), now()))
            db.commit()
            stats["inserted"] = int(stats["inserted"]) + 1
            if extract_bodies:
                time.sleep(REQUEST_PAUSE_SECONDS)
    except Exception as error:
        stats["errors"] = str(error)
        logging.error("%s: %s", feed_url, error)
    db.execute("UPDATE collection_runs SET completed_at=?,entries_seen=?,inserted=?,skipped=?,errors=? WHERE id=?", (now(), stats["seen"], stats["inserted"], stats["skipped"], stats["errors"], run_id))
    db.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Indian English RSS articles into SQLite.")
    parser.add_argument("--db", default="data/articles.db")
    parser.add_argument("--backfill", action="store_true", help="ingest every item currently exposed by the configured feeds; RSS archive depth varies by publisher")
    parser.add_argument("--verify-feeds", action="store_true", help="only test configured feed URLs and report status")
    parser.add_argument("--no-body", action="store_true", help="store RSS metadata only; skip permitted article-body extraction")
    parser.add_argument("--source", choices=sorted(FEEDS), help="collect one publisher only")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    selected = {args.source: FEEDS[args.source]} if args.source else FEEDS
    if args.verify_feeds:
        failures = 0
        for source, urls in selected.items():
            for url in urls:
                try:
                    parsed = feedparser.parse(fetch(url))
                    valid = len(parsed.entries)
                    print(f"OK     {source}: {url} ({valid} entries)")
                    if not valid:
                        failures += 1
                except Exception as error:
                    failures += 1
                    print(f"FAILED {source}: {url} ({error})")
                time.sleep(REQUEST_PAUSE_SECONDS)
        raise SystemExit(1 if failures else 0)
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(args.db)
    ensure_schema(db)
    for source, urls in selected.items():
        for url in urls:
            stats = collect_feed(db, source, url, not args.no_body, args.backfill)
            print(f"{source}: seen={stats['seen']} inserted={stats['inserted']} skipped={stats['skipped']} errors={stats['errors'] or 'none'}")
    print("\nStored articles by source:")
    for source, count in db.execute("SELECT source,COUNT(*) FROM articles GROUP BY source ORDER BY source"):
        print(f"  {source}: {count}")


if __name__ == "__main__":
    main()
