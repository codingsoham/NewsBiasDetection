"""Test logit/probability ensembling between curated RoBERTa and focal-loss RoBERTa."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import sys
sys.path.append('ml')
from training_common import load_split, LABEL_TO_ID, LABELS

te = load_split('data/articles.db', 'test', headline_snippet_only=True)
gold_ids = [LABEL_TO_ID[r['label']] for r in te]

p_curated = np.load('results/curated/test_probabilities.npy')
p_focal = np.load('results/transformer_test_probabilities.npy')

print("Evaluating Ensembles on Gold Test Split:")
for w in [0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0]:
    p_ens = w * p_curated + (1.0 - w) * p_focal
    preds = np.argmax(p_ens, axis=1)
    acc = accuracy_score(gold_ids, preds)
    rep = classification_report(gold_ids, preds, target_names=LABELS, output_dict=True, zero_division=0)
print("\n" + "="*50)
print("50/50 ENSEMBLE DETAILED PERFORMANCE")
print("="*50)
p_ens = 0.5 * p_curated + 0.5 * p_focal
preds = np.argmax(p_ens, axis=1)
rep = classification_report(gold_ids, preds, target_names=LABELS, output_dict=True, zero_division=0)
cm = confusion_matrix(gold_ids, preds, labels=range(4))

print(f"Accuracy:    {accuracy_score(gold_ids, preds):.4f}")
print(f"Macro-F1:    {rep['macro avg']['f1-score']:.4f}")
print(f"Weighted-F1: {rep['weighted avg']['f1-score']:.4f}")

print("\nPer-Class Metrics:")
for k in LABELS:
    p = rep[k]['precision']
    r = rep[k]['recall']
    f = rep[k]['f1-score']
    s = int(rep[k]['support'])
    print(f"  {k:15}: Prec={p:.3f}, Recall={r:.3f}, F1={f:.3f} (support={s})")

print("\nConfusion Matrix (Row=Gold, Col=Pred):")
print(f"{'':15} " + " ".join(f"{k:>12}" for k in LABELS))
for i, row_label in enumerate(LABELS):
    print(f"{row_label:15} " + " ".join(f"{cm[i, j]:12d}" for j in range(4)))
