"""Evaluate raw transformer vs Bayesian blended model on fresh live benchmark."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import sys
sys.path.append('ml')
sys.path.append('backend')
from training_common import LABELS, LABEL_TO_ID
from priors import get_outlet_prior, blend_probabilities

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model_dir = 'models/best/best'

tok = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device).eval()

items = json.loads(Path('data/fresh_live_benchmark_2026.json').read_text(encoding='utf-8'))
gold_ids = [LABEL_TO_ID[x['label']] for x in items]

# 1. Raw Transformer forward pass
raw_preds = []
blended_preds = []

with torch.no_grad():
    for item in items:
        text = f"{item['title']} {item['snippet']}"
        batch = tok(text, return_tensors='pt', truncation=True, max_length=512).to(device)
        logits = model(**batch).logits[0]
        probs = torch.softmax(logits, dim=0).cpu().numpy()
        p_dict = {LABELS[j]: float(probs[j]) for j in range(4)}

        # Raw argmax
        raw_preds.append(int(np.argmax(probs)))

        # Bayesian blended
        b_dict = blend_probabilities(p_dict, item['source'])
        top_b = max(b_dict, key=b_dict.get)
        blended_preds.append(LABEL_TO_ID[top_b])

acc_raw = accuracy_score(gold_ids, raw_preds)
rep_raw = classification_report(gold_ids, raw_preds, target_names=LABELS, output_dict=True, zero_division=0)

acc_blended = accuracy_score(gold_ids, blended_preds)
rep_blended = classification_report(gold_ids, blended_preds, target_names=LABELS, output_dict=True, zero_division=0)

print("="*60)
print("COMPARISON ON LIVE FRESH INDIAN BENCHMARK (40 ARTICLES)")
print("="*60)
print(f"Raw Transformer Alone:       Accuracy = {acc_raw:.4f} | Macro-F1 = {rep_raw['macro avg']['f1-score']:.4f}")
print(f"Production (With Priors):    Accuracy = {acc_blended:.4f} | Macro-F1 = {rep_blended['macro avg']['f1-score']:.4f}")

print("\nRaw Transformer Per-Class F1:")
for k in LABELS:
    print(f"  {k:15}: P={rep_raw[k]['precision']:.3f}, R={rep_raw[k]['recall']:.3f}, F1={rep_raw[k]['f1-score']:.3f}")

print("\nProduction Model Per-Class F1:")
for k in LABELS:
    print(f"  {k:15}: P={rep_blended[k]['precision']:.3f}, R={rep_blended[k]['recall']:.3f}, F1={rep_blended[k]['f1-score']:.3f}")

out_comp = {
    'raw_transformer': {'accuracy': acc_raw, 'macro_f1': rep_raw['macro avg']['f1-score'], 'report': rep_raw},
    'production_blended': {'accuracy': acc_blended, 'macro_f1': rep_blended['macro avg']['f1-score'], 'report': rep_blended}
}
Path('results/live_benchmark_comparison.json').write_text(json.dumps(out_comp, indent=2))

