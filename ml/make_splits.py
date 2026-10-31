"""Create leakage-safe Phase 3 train/validation/test splits and a data card."""
from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path

from labeling_common import LABELS, connect, ensure_labeling_schema, load_dotenv, utc_now

HELD_OUT_TEST_SOURCES = ("NDTV", "India Today")
SEED = 20261029


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic, provenance-safe Phase 3 splits.")
    parser.add_argument("--db")
    parser.add_argument("--reviewer", default="codingsoham")
    args = parser.parse_args()
    load_dotenv()
    db = connect(args.db)
    ensure_labeling_schema(db)
    gold = db.execute("""SELECT h.article_id, h.label, COALESCE(a.source,'Unknown') source
                         FROM human_reviews h JOIN articles a ON a.id=h.article_id
                         WHERE h.reviewer_id=? ORDER BY h.article_id""", (args.reviewer,)).fetchall()
    if len(gold) != 250:
        raise SystemExit(f"Expected 250 completed gold reviews for {args.reviewer}; found {len(gold)}.")
    held = [r for r in gold if r['source'] in HELD_OUT_TEST_SOURCES]
    remaining = [r for r in gold if r['source'] not in HELD_OUT_TEST_SOURCES]
    # Target exactly half of gold data for test, while keeping label proportions.
    totals = Counter(r['label'] for r in gold)
    target = {label: round(totals[label] / 2) for label in LABELS}
    # Adjust rounding deterministically to exactly 125.
    while sum(target.values()) < 125:
        target[max(LABELS, key=lambda label: (totals[label] / 2 - target[label], label))] += 1
    needed = {label: target[label] - sum(r['label'] == label for r in held) for label in LABELS}
    if any(value < 0 for value in needed.values()):
        raise SystemExit("Held-out publishers overfill a test label; choose different held-out sources.")
    rng = random.Random(SEED)
    by_label: dict[str, list] = defaultdict(list)
    for row in remaining:
        by_label[row['label']].append(row)
    test = list(held)
    for label in LABELS:
        rng.shuffle(by_label[label])
        test.extend(by_label[label][:needed[label]])
    test_ids = {r['article_id'] for r in test}
    validation = [r for r in gold if r['article_id'] not in test_ids]
    if len(test) != 125 or len(validation) != 125:
        raise SystemExit(f"Split size error: test={len(test)}, validation={len(validation)}")
    train = db.execute("""SELECT s.article_id, s.label, COALESCE(a.source,'Unknown') source
                          FROM silver_labels s JOIN articles a ON a.id=s.article_id
                          WHERE COALESCE(a.source,'Unknown') NOT IN (?, ?)
                            AND NOT EXISTS (SELECT 1 FROM human_reviews h WHERE h.article_id=s.article_id)""", HELD_OUT_TEST_SOURCES).fetchall()
    db.execute("DELETE FROM dataset_splits")
    now = utc_now()
    db.executemany("INSERT INTO dataset_splits (article_id,split,label,provenance,source,created_at) VALUES (?,?,?,?,?,?)",
                   [(r['article_id'], 'train', r['label'], 'silver', r['source'], now) for r in train] +
                   [(r['article_id'], 'validation', r['label'], 'gold', r['source'], now) for r in validation] +
                   [(r['article_id'], 'test', r['label'], 'gold', r['source'], now) for r in test])
    db.commit()
    counts = {split: Counter(r['label'] for r in rows) for split, rows in [('train', train), ('validation', validation), ('test', test)]}
    docs = Path(__file__).resolve().parents[1] / 'docs'; docs.mkdir(exist_ok=True)
    lines = ['# Data card', '', '## Split policy', '', f'- Seed: `{SEED}`.', '- Training contains silver labels only; all 250 human-reviewed gold records are excluded.', '- Validation and test contain 125 gold records each.', f'- Test-only publishers: {", ".join(HELD_OUT_TEST_SOURCES)}. Their silver records are excluded from training.', '', '## Counts', '', '| Split | Provenance | Total | LEFT | CENTER | RIGHT | NOT_POLITICAL |', '|---|---:|---:|---:|---:|---:|---:|']
    for split, provenance in [('train','silver'), ('validation','gold'), ('test','gold')]:
        c = counts[split]; lines.append(f'| {split} | {provenance} | {sum(c.values())} | {c["LEFT"]} | {c["CENTER"]} | {c["RIGHT"]} | {c["NOT_POLITICAL"]} |')
    source_rows = db.execute("SELECT source, COUNT(*) n FROM dataset_splits GROUP BY source ORDER BY n DESC, source").fetchall()
    lines += ['', '## Publisher coverage', '', '| Publisher | Records across all splits |', '|---|---:|']
    lines.extend(f'| {row["source"]} | {row["n"]} |' for row in source_rows)
    lines += ['', '## Sources and limitations', '', '- Sources: The Hindu, Indian Express, NDTV, Times of India, Hindustan Times, ThePrint, India Today, and Firstpost.', '- The corpus is publisher- and class-imbalanced, especially for RIGHT; use weighted loss and report macro-F1.', '- Silver labels come from local Qwen double-pass agreement. Gold labels were manually reviewed, but the review interface displayed suggestions, so gold agreement estimates may be subject to anchoring bias.', '- Article text is local research data and must not be served by the API.']
    (docs / 'data-card.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Train silver: {len(train)}; validation gold: {len(validation)}; test gold: {len(test)}')
    for split in ('train','validation','test'):
        print(split, dict(counts[split]))


if __name__ == '__main__':
    main()
