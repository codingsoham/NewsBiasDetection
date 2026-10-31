"""Curate and balance training data by fixing silver label noise and adding balanced Indian sources.

Strict Leakage-Safety:
- Gold Test (125 items) and Gold Validation (125 items) are 100% held-out and UNTOUCHED.
- Held-out publishers (NDTV, India Today) are NEVER added to training.
- Clean Rule 5 non-political items misclassified as CENTER in train.
- Add genuine political records from OpIndia, Swarajya, Organiser (RIGHT) and The Wire, Scroll (LEFT).
"""
from __future__ import annotations
import re
import sqlite3
from collections import Counter
from pathlib import Path

POL_ENTITIES = re.compile(
    r'\b(bjp|congress|modi|rahul|amit shah|shah|kharge|kejriwal|aap|tmc|yogi|cpim|rjd|sp|dmk|bjd|nda|upa|'
    r'india bloc|election|poll|voter|parliament|lok sabha|rajya sabha|assembly|minister|cabinet|government|govt|'
    r'governor|supreme court|high court|court|judge|cji|constitution|secular|hindutva|sanatan|waqf|caa|nrc|'
    r'reservation|caste census|protest|rally|strike|ordinance|scheme|bill|manifesto|scam|corruption|cbi|ed|nia|'
    r'pakistan|china border|foreign minister|diplomat|geopolitics|treaty|sovereignty)\b',
    re.IGNORECASE
)

NON_POL_TOPICS = re.compile(
    r'\b(cricket|match|wicket|innings|batting|bowling|football|fifa|messi|ronaldo|ipl|wpl|tennis|badminton|'
    r'olympics|trophy|goal|striker|coach|gold seized|smuggling|body found|road accident|bus accident|fire breaks out|'
    r'car crash|robbery|theft|snatching|narcotics|drugs seized|ganja|contraband|cyclone|weather|rainfall|'
    r'red alert|earthquake|monsoon|flood|heatwave|temperature|snowfall|sensex|nifty|q[1-4]|ebitda|quarterly profit|'
    r'revenue up|stock market|dividend|mutual fund|bullion|gold price|gold rate|box office|movie review|trailer|'
    r'actor|actress|bollywood|hollywood|tollywood|ott|cinema|film|wedding|recipe|horoscope|elephant|wildlife|zoo)\b',
    re.IGNORECASE
)

HELD_OUT_SOURCES = {"NDTV", "India Today"}


def audit_splits(db_path: str = 'data/articles.db'):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    print("=== CURRENT DATASET SPLITS ===")
    counts = db.execute("SELECT split, label, COUNT(*) as c FROM dataset_splits GROUP BY split, label").fetchall()
    for row in counts:
        print(f"  {row['split']:12} | {row['label']:15} | {row['c']}")

    # 1. Inspect noise in train CENTER
    train_rows = db.execute(
        """SELECT d.article_id, d.label, a.title, a.snippet, a.source
           FROM dataset_splits d JOIN articles a ON a.id=d.article_id
           WHERE d.split='train'"""
    ).fetchall()

    reclass_to_not_pol = []
    for r in train_rows:
        text = f"{r['title'] or ''} {r['snippet'] or ''}"
        if r['label'] == 'CENTER':
            if NON_POL_TOPICS.search(text) and not POL_ENTITIES.search(text):
                reclass_to_not_pol.append(r['article_id'])

    print(f"\nRule 5 Clean: {len(reclass_to_not_pol)} CENTER articles in train will be corrected to NOT_POLITICAL.")

    # 2. Inspect new candidate articles
    candidates = db.execute(
        """SELECT id, source, title, snippet FROM articles
           WHERE id NOT IN (SELECT article_id FROM dataset_splits)
             AND source NOT IN ('NDTV', 'India Today')"""
    ).fetchall()

    additions = []
    for r in candidates:
        text = f"{r['title'] or ''} {r['snippet'] or ''}"
        src = (r['source'] or '').lower().strip()
        is_pol = bool(POL_ENTITIES.search(text))
        is_non_pol = bool(NON_POL_TOPICS.search(text)) and not is_pol

        if any(s in src for s in ('opindia', 'swarajya', 'organiser')):
            if is_pol:
                additions.append((r['id'], 'train', 'RIGHT', 'silver', r['source']))
            elif is_non_pol:
                additions.append((r['id'], 'train', 'NOT_POLITICAL', 'silver', r['source']))
        elif any(s in src for s in ('thewire', 'scroll')):
            if is_pol:
                additions.append((r['id'], 'train', 'LEFT', 'silver', r['source']))
            elif is_non_pol:
                additions.append((r['id'], 'train', 'NOT_POLITICAL', 'silver', r['source']))
        elif any(s in src for s in ('deccan herald', 'free', 'hindu', 'express', 'theprint')):
            if is_pol:
                additions.append((r['id'], 'train', 'CENTER', 'silver', r['source']))
            elif is_non_pol:
                additions.append((r['id'], 'train', 'NOT_POLITICAL', 'silver', r['source']))

    add_counts = Counter(x[2] for x in additions)
    print(f"New High-Confidence Additions to train: {len(additions)}")
    for lbl, count in add_counts.items():
        print(f"  + {lbl:15}: {count}")

    print("\n--- SAMPLE RIGHT ADDITIONS ---")
    for r in [a for a in additions if a[2] == 'RIGHT'][:5]:
        art = db.execute("SELECT title FROM articles WHERE id=?", (r[0],)).fetchone()
        t = (art['title'] or '')[:65].encode('ascii', 'ignore').decode()
        print(f"  [{r[4]}] {t}")

    print("\n--- SAMPLE LEFT ADDITIONS ---")
    for r in [a for a in additions if a[2] == 'LEFT'][:5]:
        art = db.execute("SELECT title FROM articles WHERE id=?", (r[0],)).fetchone()
        t = (art['title'] or '')[:65].encode('ascii', 'ignore').decode()
        print(f"  [{r[4]}] {t}")

    print("\n--- SAMPLE NOT_POLITICAL ADDITIONS ---")
    for r in [a for a in additions if a[2] == 'NOT_POLITICAL'][:5]:
        art = db.execute("SELECT title FROM articles WHERE id=?", (r[0],)).fetchone()
        t = (art['title'] or '')[:65].encode('ascii', 'ignore').decode()
        print(f"  [{r[4]}] {t}")

    return reclass_to_not_pol, additions


def apply_curation(db_path: str = 'data/articles.db', dry_run: bool = True):
    reclass_ids, additions = audit_splits(db_path)
    if dry_run:
        print("\n[DRY RUN] No changes committed to database. Run with --apply to commit.")
        return

    db = sqlite3.connect(db_path)
    # 1. Update noisy CENTER records to NOT_POLITICAL in train split
    if reclass_ids:
        placeholders = ','.join('?' * len(reclass_ids))
        db.execute(
            f"UPDATE dataset_splits SET label='NOT_POLITICAL' WHERE split='train' AND article_id IN ({placeholders})",
            reclass_ids
        )
        print(f"Updated {len(reclass_ids)} noisy records in train to NOT_POLITICAL.")

    # 2. Insert new curated training records
    if additions:
        now = "2026-10-30T10:30:00Z"
        db.executemany(
            "INSERT INTO dataset_splits (article_id, split, label, provenance, source, created_at) VALUES (?,?,?,?,?,?)",
            [(a[0], a[1], a[2], a[3], a[4], now) for a in additions]
        )
        print(f"Inserted {len(additions)} new curated records into train split.")

    db.commit()

    print("\n=== UPDATED TRAIN BREAKDOWN ===")
    updated = db.execute("SELECT label, COUNT(*) FROM dataset_splits WHERE split='train' GROUP BY label").fetchall()
    for lbl, count in updated:
        print(f"  {lbl:15}: {count}")

    print("\nValidation & Test splits remain 100% strictly untouched:")
    for sp in ('validation', 'test'):
        sp_counts = db.execute("SELECT label, COUNT(*) FROM dataset_splits WHERE split=? GROUP BY label", (sp,)).fetchall()
        print(f"  {sp:12}: {dict(sp_counts)}")


if __name__ == '__main__':
    import sys
    dry = '--apply' not in sys.argv
    apply_curation(dry_run=dry)
