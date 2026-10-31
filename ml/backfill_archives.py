"""Historical, robots-respecting sitemap backfill for the Phase 1 publishers.

Run this after collect_indian.py. It uses only sitemap locations declared in a
publisher's robots.txt, and stops at the requested database total.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import logging
import re
import sqlite3
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import deque

from collect_indian import FEEDS, REQUEST_PAUSE_SECONDS, body_for, ensure_schema, fetch, is_english, normalise_url, now, robots_allow

ARCHIVE_HINT = re.compile(r"politic|election|government|governance|parliament|bjp|congress|modi|opposition|national|india|court|minister|policy|state", re.I)
NON_ARTICLE_EXTENSION = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|svg|mp4|webm|pdf|xml)(?:$|[?#])", re.I)


def sitemap_locations(source: str) -> list[str]:
    """Read only Sitemap declarations published by the site's robots.txt."""
    seed = next(iter(FEEDS[source]))
    parsed = urllib.parse.urlsplit(seed)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots = fetch(robots_url).decode("utf-8", errors="replace")
    locations = [line.split(":", 1)[1].strip() for line in robots.splitlines() if line.lower().startswith("sitemap:")]
    return [url for url in locations if url.startswith(("http://", "https://"))]


def xml_locations(data: bytes) -> tuple[bool, list[str]]:
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    root = ET.fromstring(data)
    is_index = root.tag.rsplit("}", 1)[-1] == "sitemapindex"
    return is_index, [element.text.strip() for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "loc" and element.text]


def archive_candidates(source: str, max_sitemaps: int = 200) -> list[str]:
    queue = deque(sitemap_locations(source))
    seen: set[str] = set()
    articles: list[str] = []
    while queue and len(seen) < max_sitemaps:
        sitemap = queue.popleft()
        if sitemap in seen:
            continue
        seen.add(sitemap)
        try:
            is_index, locations = xml_locations(fetch(sitemap))
        except Exception as error:
            logging.warning("%s sitemap failed: %s", source, error)
            continue
        if is_index:
            queue.extend(locations)
        else:
            articles.extend(locations)
        time.sleep(REQUEST_PAUSE_SECONDS)
    # Preserve sitemap order (normally newest first), retaining only pages from
    # the publisher's own domain family—not CDN image assets listed in sitemaps.
    publisher_domain = urllib.parse.urlsplit(next(iter(FEEDS[source]))).netloc.lower().removeprefix("www.")
    return list(dict.fromkeys(
        url for url in articles
        if ARCHIVE_HINT.search(url)
        and not NON_ARTICLE_EXTENSION.search(url)
        and urllib.parse.urlsplit(url).netloc.lower().removeprefix("www.").endswith(publisher_domain)
    ))


def add_articles(db: sqlite3.Connection, source: str, urls: list[str], target: int, delay: float) -> tuple[int, int, int]:
    robots: dict = {}
    inserted = skipped = examined = 0
    for raw_url in urls:
        if db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] >= target:
            break
        examined += 1
        url = normalise_url(raw_url)
        if db.execute("SELECT 1 FROM articles WHERE normalized_url=?", (url,)).fetchone():
            skipped += 1
            continue
        text = body_for(url, robots)
        if not text or not is_english(text):
            skipped += 1
            time.sleep(delay)
            continue
        # A title/snippet is retained as a short, local fallback. Phase 2 labels text.
        title = text[:180].split(".")[0].strip() or "Untitled archived article"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if db.execute("SELECT 1 FROM articles WHERE content_hash=?", (digest,)).fetchone():
            skipped += 1
            continue
        db.execute("INSERT INTO articles (source,url,normalized_url,title,snippet,text,content_hash,published_at,fetched_at) VALUES (?,?,?,?,?,?,?,?,?)", (source, url, url, title, text[:500], text, digest, None, now()))
        db.commit()
        inserted += 1
        time.sleep(delay)
    return examined, inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill the existing article database from declared publisher sitemaps.")
    parser.add_argument("--db", default="data/articles.db")
    parser.add_argument("--target", type=int, default=3000)
    parser.add_argument("--source", choices=sorted(FEEDS))
    parser.add_argument("--delay", type=float, default=REQUEST_PAUSE_SECONDS)
    parser.add_argument("--list-only", action="store_true", help="report archive candidates without downloading articles")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db = sqlite3.connect(args.db)
    ensure_schema(db)
    sources = [args.source] if args.source else list(FEEDS)
    for source in sources:
        if db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] >= args.target:
            break
        try:
            urls = archive_candidates(source)
            print(f"{source}: {len(urls)} political/national archive candidates discovered")
            if args.list_only:
                continue
            seen, inserted, skipped = add_articles(db, source, urls, args.target, args.delay)
            print(f"{source}: examined={seen} inserted={inserted} skipped={skipped}")
        except Exception as error:
            logging.error("%s archive discovery failed: %s", source, error)
    total = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    with_text = db.execute("SELECT COUNT(*) FROM articles WHERE text IS NOT NULL AND length(text)>0").fetchone()[0]
    print(f"Total articles={total}; with text={with_text}; target={args.target}")


if __name__ == "__main__":
    main()
