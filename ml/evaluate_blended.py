"""Evaluate Bayesian prior blending on top of model probabilities for the gold test split."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

sys.path.append('ml')
sys.path.append('backend')
from training_common import load_split, LABEL_TO_ID, LABELS
from priors import blend_probabilities


def evaluate_blended(prob_path: str, alpha: float = 0.65, out_name: str = 'curated_blended'):
    te = load_split('data/articles.db', 'test', headline_snippet_only=True)
    raw_probs = np.load(prob_path)
    gold_ids = [LABEL_TO_ID[r['label']] for r in te]

    blended_preds = []
    for i, r in enumerate(te):
        t_probs = {LABELS[j]: float(raw_probs[i][j]) for j in range(4)}
        b_probs = blend_probabilities(t_probs, r['source'], alpha=alpha)
        blended_preds.append(LABEL_TO_ID[max(b_probs, key=b_probs.get)])

    acc = accuracy_score(gold_ids, blended_preds)
    report = classification_report(gold_ids, blended_preds, target_names=LABELS, output_dict=True, zero_division=0)
    cm = confusion_matrix(gold_ids, blended_preds, labels=range(4))

    print("="*50)
    print(f"BLENDED EVALUATION (alpha={alpha}):")
    print(f"Accuracy:    {acc:.4f}")
    print(f"Macro-F1:    {report['macro avg']['f1-score']:.4f}")
    print(f"Weighted-F1: {report['weighted avg']['f1-score']:.4f}")
    print("\nPer-class breakdown:")
    for k in LABELS:
        print(f"  {k:15}: Prec={report[k]['precision']:.3f}, Recall={report[k]['recall']:.3f}, F1={report[k]['f1-score']:.3f}")

    print("\nConfusion Matrix:")
    print(f"{'':15} " + " ".join(f"{k:>12}" for k in LABELS))
    for i, row_label in enumerate(LABELS):
        print(f"{row_label:15} " + " ".join(f"{cm[i, j]:12d}" for j in range(4)))

    return acc, report, cm


if __name__ == '__main__':
    evaluate_blended('results/curated/test_probabilities.npy', alpha=0.35)
