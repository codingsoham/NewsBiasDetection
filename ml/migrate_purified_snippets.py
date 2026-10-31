"""Sanitize snippets in articles.db and re-evaluate all article predictions with pure text."""
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import DB, predict_batch
from backend.text_cleaner import clean_snippet, build_clean_evaluation_text, unescape_text, strip_publisher_watermarks

def main():
    print(f"Opening database: {DB}")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    
    # 1. Fetch all articles
    articles = conn.execute("SELECT id, source, title, snippet FROM articles ORDER BY id").fetchall()
    print(f"Total articles to process: {len(articles)}")
    
    # 2. Clean titles and snippets
    updates = []
    eval_texts = []
    sources = []
    
    for r in articles:
        raw_t = r['title'] or ''
        raw_s = r['snippet'] or ''
        
        clean_t = strip_publisher_watermarks(unescape_text(raw_t))
        clean_s = clean_snippet(clean_t, raw_s)
        
        updates.append((clean_t, clean_s if clean_s else None, r['id']))
        eval_text = build_clean_evaluation_text(clean_t, clean_s)
        eval_texts.append(eval_text)
        sources.append(r['source'])
        
    print("Updating articles table with sanitized titles and snippets...")
    conn.executemany("UPDATE articles SET title = ?, snippet = ? WHERE id = ?", updates)
    conn.commit()
    print("Articles table updated successfully.")
    
    # 3. Predict bias in batches of 64
    print("Running batched inference on purified prose (no watermarks)...")
    start_time = time.time()
    predictions = predict_batch(eval_texts, sources=sources, batch_size=64)
    elapsed = time.time() - start_time
    print(f"Inference completed in {elapsed:.1f}s ({len(predictions)/elapsed:.1f} articles/s).")
    
    # 4. Update predictions table
    pred_records = [
        (
            r['id'],
            p['LEFT'],
            p['CENTER'],
            p['RIGHT'],
            int(max(p.values()) < 0.45),
            'models/best/best (Option 1: Purified Text)'
        )
        for r, p in zip(articles, predictions)
    ]
    
    conn.executemany(
        """INSERT OR REPLACE INTO predictions (article_id, p_left, p_center, p_right, low_confidence, model_path)
           VALUES (?, ?, ?, ?, ?, ?)""",
        pred_records
    )
    conn.commit()
    print("Predictions table updated successfully.")
    
    # 5. Check specific verification articles
    test_rows = conn.execute(
        """SELECT a.id, a.source, a.title, a.snippet, p.p_left, p.p_center, p.p_right 
           FROM articles a JOIN predictions p ON p.article_id = a.id 
           WHERE a.id IN (6014, 5984) OR a.title LIKE '%Supreme Court asks EC%'"""
    ).fetchall()
    
    print("\n" + "=" * 60)
    print("VERIFICATION: Case Articles After Fix")
    print("=" * 60)
    for row in test_rows:
        print(f"Source:  {row['source']} (ID: {row['id']})")
        print(f"Title:   {row['title']}")
        print(f"Snippet: {row['snippet']}")
        print(f"Ratings: LEFT: {row['p_left']:.1%}, CENTER: {row['p_center']:.1%}, RIGHT: {row['p_right']:.1%}")
        print("-" * 60)
        
    conn.close()

if __name__ == '__main__':
    main()
