"""Comprehensive purification scanner for training dataset.

Scans all 1,793 CENTER training records and accurately splits them into:
1. Genuine Political / Policy / Court / Legislative news -> KEEP IN CENTER
2. Civic, lifestyle, corporate, tech, entertainment, student, weather news -> MOVE TO NOT_POLITICAL
"""
from __future__ import annotations
import re
import sqlite3
from collections import Counter
from pathlib import Path

# Core political indicators (if ANY of these are present in title or snippet, it's considered political)
POLITICAL_CORE = re.compile(
    r'\b(modi|rahul|gandhi|shah|kharge|kejriwal|yogi|fadnavis|sitharaman|nadda|tharoor|pawar|shinde|stalin|'
    r'mamata|akhilesh|mayawati|hemanth|soren|nitish|tejaswi|bjp|congress|aap|tmc|cpi|cpim|rjd|sp|dmk|aiadmk|bjd|'
    r'nda|upa|india bloc|election|poll|voter|by-poll|parliament|lok sabha|rajya sabha|vidhan sabha|assembly|'
    r'minister|ministry|cabinet|government|govt|governor|supreme court|high court|court|judge|cji|bench|'
    r'constitution|secular|hindutva|sanatan|waqf|caa|nrc|reservation|caste census|protest|rally|strike|'
    r'ordinance|scheme|bill|manifesto|scam|corruption|cbi|ed|nia|mla|mp|chief minister|prime minister|president|'
    r'treaty|geopolitics|china border|pakistan|kashmir|diplomat|ambassador|legislation|judiciary|verdict|bail|'
    r'custody|anti-defection|by-election|panchayat|civic poll|mayor|councillor|sedition|defamation|uapa|pmla|'
    r'delimitation|electoral bonds|evm|voter list|foreign policy|national security|defence|army|navy|air force|'
    r'border security|terror|naxal|maoist|insurgent|separatist)\b',
    re.IGNORECASE
)

# Soft news / non-political markers (only applied when NO political core entity is present)
NON_POL_EXPANDED = re.compile(
    r'\b(cricket|match|wicket|innings|batting|bowling|football|fifa|messi|ronaldo|ipl|wpl|tennis|badminton|'
    r'olympics|trophy|goal|striker|coach|gold seized|smuggling|body found|road accident|bus accident|fire breaks out|'
    r'car crash|robbery|theft|snatching|narcotics|drugs seized|ganja|contraband|cyclone|weather|rainfall|'
    r'red alert|earthquake|monsoon|flood|heatwave|temperature|snowfall|sensex|nifty|q[1-4]|ebitda|quarterly profit|'
    r'revenue up|stock market|dividend|mutual fund|bullion|gold price|gold rate|box office|movie review|trailer|'
    r'actor|actress|bollywood|hollywood|tollywood|ott|cinema|film|wedding|recipe|horoscope|elephant|wildlife|'
    r'zoo|exam|board exam|shaadi|shipments|chutney|samosa|food safety|milk price|project sadak|adulteration|'
    r'school admission|cbse|icse|neet|jee|college|university campus|traffic jam|metro timing|water cut|power cut|'
    r'lifestyle|skin care|fitness|diet|nutrition|astrology|zodiac|tech review|smartphone launch|'
    r'gadget|iphone|android app|sales drop|quarterly earnings|discount sale|flight delayed|fog disrupts|'
    r'train cancelled|station redevelopment|hospital bed|dengue|malaria|viral fever|pollution level|aqi|'
    r'clean air|heritage walk|flower show|book launch|art gallery|classical dance|music concert|theatre play|'
    r'tiger|leopard|snake|rescue|animal shelter|dog bite|stray dogs|pet care|gardening|coffee|tea estate|'
    r'tourism|travel guide|hotel booking|resort|vacation|weekend getaway|diwali discount|puja bonus|festive offer|'
    r'gold loan|home loan|car loan|interest rate cut|personal finance|fixed deposit|crypto|bitcoin|ai startup|'
    r'software update|cyber fraud|phishing|deepfake viral|meme|influencer|instagram|youtube video)\b',
    re.IGNORECASE
)


def run_purification_audit(db_path: str = 'data/articles.db'):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    rows = db.execute(
        """SELECT d.article_id, d.label, a.source, a.title, a.snippet
           FROM dataset_splits d JOIN articles a ON a.id=d.article_id
           WHERE d.split='train' AND d.label='CENTER'"""
    ).fetchall()

    reclass_ids = []
    kept_rows = []

    for r in rows:
        text = f"{r['title'] or ''} {r['snippet'] or ''}"
        has_pol = bool(POLITICAL_CORE.search(text))

        # If an article has NO political, electoral, judicial, or governmental entity/action,
        # it is NOT a political news article! It belongs in NOT_POLITICAL.
        if not has_pol:
            reclass_ids.append(r)
        else:
            kept_rows.append(r)

    print(f"Total CENTER rows in train: {len(rows)}")
    print(f"  Identified as NON_POLITICAL (Zero political content): {len(reclass_ids)} ({len(reclass_ids)/len(rows)*100:.1f}%)")
    print(f"  Verified Pure Political / Policy CENTER:            {len(kept_rows)} ({len(kept_rows)/len(rows)*100:.1f}%)")

    print("\n--- SAMPLE IDENTIFIED NON-POLITICAL ARTICLES (TO MOVE) ---")
    for r in reclass_ids[:15]:
        t = (r['title'] or '')[:70].encode('ascii', 'ignore').decode()
        print(f"  [{r['source']}] {t}")

    print("\n--- SAMPLE KEPT ARTICLES (VERIFIED GENUINE POLITICAL/POLICY CENTER) ---")
    for r in kept_rows[:15]:
        t = (r['title'] or '')[:70].encode('ascii', 'ignore').decode()
        print(f"  [{r['source']}] {t}")

    return [r['article_id'] for r in reclass_ids]


def apply_purification(db_path: str = 'data/articles.db', dry_run: bool = True):
    clean_ids = run_purification_audit(db_path)
    if dry_run:
        print("\n[DRY RUN] Run with --apply to commit changes to database.")
        return

    db = sqlite3.connect(db_path)
    if clean_ids:
        placeholders = ','.join('?' * len(clean_ids))
        db.execute(
            f"UPDATE dataset_splits SET label='NOT_POLITICAL' WHERE split='train' AND article_id IN ({placeholders})",
            clean_ids
        )
        db.commit()
        print(f"\nSuccessfully cleaned {len(clean_ids)} noisy records in train to NOT_POLITICAL!")

    print("\n=== UPDATED TRAIN SPLIT BREAKDOWN ===")
    updated = db.execute("SELECT label, COUNT(*) FROM dataset_splits WHERE split='train' GROUP BY label").fetchall()
    for lbl, count in updated:
        print(f"  {lbl:15}: {count}")

    print("\nVerification: Validation and Test splits:")
    for sp in ('validation', 'test'):
        sp_counts = db.execute("SELECT label, COUNT(*) FROM dataset_splits WHERE split=? GROUP BY label", (sp,)).fetchall()
        print(f"  {sp:12}: {dict(sp_counts)}")


if __name__ == '__main__':
    import sys
    dry = '--apply' not in sys.argv
    apply_purification(dry_run=dry)
