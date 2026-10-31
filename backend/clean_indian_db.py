"""One-time purge of non-Indian and foreign domestic news from articles.db, followed by re-clustering."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sqlite3
from backend.indian_filter import classify_indian_news
from backend.ingest import cluster_stories, DB

def clean_database():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=30000;")

    # 1. Inspect existing articles
    articles = c.execute("SELECT id, title, snippet FROM articles").fetchall()
    non_indian_ids = []
    for a in articles:
        is_ind, reason = classify_indian_news(a['title'], a['snippet'])
        if not is_ind:
            non_indian_ids.append(a['id'])

    print(f"Total articles in DB: {len(articles)}")
    print(f"Non-Indian articles to purge: {len(non_indian_ids)}")

    if non_indian_ids:
        batch_size = 500
        for i in range(0, len(non_indian_ids), batch_size):
            batch = non_indian_ids[i:i+batch_size]
            placeholders = ','.join('?' for _ in batch)
            c.execute(f"DELETE FROM predictions WHERE article_id IN ({placeholders})", batch)
            c.execute(f"DELETE FROM story_articles WHERE article_id IN ({placeholders})", batch)
            c.execute(f"DELETE FROM articles WHERE id IN ({placeholders})", batch)
        c.commit()
        print(f"Purged {len(non_indian_ids)} non-Indian articles from database.")

    # 2. Re-cluster stories strictly from Indian news
    stories_count, links_count = cluster_stories(c, threshold=0.68, recent_only=False)
    print(f"Re-clustered Indian stories: {stories_count} stories with {links_count} links.")

    # 3. Final purge of any residual foreign/unrelated story titles
    stories = c.execute("SELECT id, title FROM stories").fetchall()
    purged_stories = 0
    for s in stories:
        if not classify_indian_news(s['title'])[0]:
            c.execute("DELETE FROM story_articles WHERE story_id=?", (s['id'],))
            c.execute("DELETE FROM stories WHERE id=?", (s['id'],))
            purged_stories += 1
    c.commit()

    stories = c.execute("SELECT id, title FROM stories").fetchall()
    foreign_stories = [s for s in stories if not classify_indian_news(s['title'])[0]]
    print(f"Purged residual stories: {purged_stories}. Total clean Indian stories: {len(stories)}. Foreign stories remaining: {len(foreign_stories)} (MUST BE 0)")
    c.close()

if __name__ == '__main__':
    clean_database()
