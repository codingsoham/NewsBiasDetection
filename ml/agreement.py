"""Report LLM-vs-gold agreement without contaminating test labels."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from labeling_common import LABELS, connect, ensure_labeling_schema, load_dotenv


def kappa(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    observed = sum(a == b for a, b in pairs) / len(pairs)
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum((first[label] / len(pairs)) * (second[label] / len(pairs)) for label in LABELS)
    return 0.0 if expected == 1 else (observed - expected) / (1 - expected)


def report(name: str, pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return f"{name}: no overlapping LLM/gold labels"
    matrix = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    for predicted, actual in pairs:
        matrix[actual][predicted] += 1
    accuracy = sum(p == g for p, g in pairs) / len(pairs)
    lines = [f"{name}: n={len(pairs)}, accuracy={accuracy:.3f}, Cohen's kappa={kappa(pairs):.3f}", "gold\\llm  " + "  ".join(f"{x:>12}" for x in LABELS)]
    lines.extend(f"{gold:>10}  " + "  ".join(f"{matrix[gold][llm]:>12}" for llm in LABELS) for gold in LABELS)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    parser.add_argument("--reviewer", help="restrict to a reviewer")
    args = parser.parse_args()
    load_dotenv()
    db = connect(args.db)
    ensure_labeling_schema(db)
    sql = """SELECT a.source, h.reviewer_id, h.label AS gold, s.label AS llm
             FROM human_reviews h JOIN silver_labels s ON s.article_id=h.article_id
             JOIN articles a ON a.id=h.article_id"""
    params: tuple = ()
    if args.reviewer:
        sql += " WHERE h.reviewer_id=?"
        params = (args.reviewer,)
    rows = db.execute(sql, params).fetchall()
    overall = [(row["llm"], row["gold"]) for row in rows]
    print(report("Overall silver LLM vs gold", overall))
    by_source: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[row["source"] or "Unknown"].append((row["llm"], row["gold"]))
    for source in sorted(by_source):
        print("\n" + report(f"Source: {source}", by_source[source]))


if __name__ == "__main__":
    main()
