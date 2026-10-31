"""Audit training set label quality across all classes."""
from __future__ import annotations
import random
import sqlite3
import json

db = sqlite3.connect('data/articles.db')
db.row_factory = sqlite3.Row

random.seed(42)

print("="*70)
print("SAMPLING AND AUDITING TRAINING LABELS ACROSS ALL 4 CLASSES")
print("="*70)

for target_label in ['RIGHT', 'LEFT', 'CENTER', 'NOT_POLITICAL']:
    print(f"\n>>> AUDITING CLASS: {target_label} <<<")
    rows = db.execute(
        """SELECT d.article_id, d.label, d.provenance, a.source, a.title, a.snippet,
                  (SELECT rationale FROM llm_annotations WHERE article_id=d.article_id LIMIT 1) as llm_rationale
           FROM dataset_splits d JOIN articles a ON a.id=d.article_id
           WHERE d.split='train' AND d.label=?
           ORDER BY RANDOM() LIMIT 5""",
        (target_label,)
    ).fetchall()

    for idx, r in enumerate(rows, 1):
        t = (r['title'] or '')[:75].encode('ascii', 'ignore').decode()
        s = (r['snippet'] or '')[:100].encode('ascii', 'ignore').decode()
        src = r['source'] or 'Unknown'
        prov = r['provenance']
        rat = (r['llm_rationale'] or 'N/A')[:80].encode('ascii', 'ignore').decode()

        print(f"\n[{idx}] ID: {r['article_id']} | Source: {src} | Provenance: {prov}")
        print(f"    Title:   {t}")
        print(f"    Snippet: {s}")
print("\n" + "="*70)
print("DEEP DIVE: ANALYZING 'CENTER' CLASS PURITY (POLITICAL VS SOFT/CIVIC)")
print("="*70)

import re
POL_MARKERS = re.compile(
    r'\b(govt|government|minister|ministry|cabinet|parliament|bjp|congress|aap|modi|rahul|shah|'
    r'election|poll|vote|court|judge|sc|hc|police|cbi|ed|policy|bill|ordinance|scheme|cm|pm|mla|mp|assembly)\b',
    re.I
)

center_rows = db.execute(
    """SELECT a.id, a.source, a.title, a.snippet
       FROM dataset_splits d JOIN articles a ON a.id=d.article_id
       WHERE d.split='train' AND d.label='CENTER'"""
).fetchall()

has_pol, no_pol = 0, 0
sample_soft = []
for r in center_rows:
    text = f"{r['title'] or ''} {r['snippet'] or ''}"
    if POL_MARKERS.search(text):
        has_pol += 1
    else:
        no_pol += 1
        if len(sample_soft) < 5:
            sample_soft.append((r['source'], r['title']))

print(f"Total train CENTER records: {len(center_rows)}")
print(f"  Real Political / Policy CENTER: {has_pol} ({has_pol/len(center_rows)*100:.1f}%)")
print(f"  Soft / Civic / Non-policy CENTER: {no_pol} ({no_pol/len(center_rows)*100:.1f}%)")
print("\nSample Soft/Civic articles currently labeled CENTER:")
for src, tit in sample_soft:
    print(f"  [{src}] {tit[:65].encode('ascii', 'ignore').decode()}")


