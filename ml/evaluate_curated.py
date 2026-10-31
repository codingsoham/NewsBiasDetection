"""Evaluate the curated RoBERTa model on the leakage-safe gold test split and compare."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import classification_report, confusion_matrix
import sys
sys.path.append('ml')
from training_common import LABELS, LABEL_TO_ID, load_split


def evaluate_model(model_dir: str, db_path: str = 'data/articles.db', out_dir: str = 'results/curated'):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading model from {model_dir} on {device}...")

    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device).eval()

    test_rows = load_split(db_path, 'test', headline_snippet_only=True)
    gold_labels = [r['label'] for r in test_rows]
    gold_ids = [LABEL_TO_ID[l] for l in gold_labels]

    probs = []
    with torch.no_grad():
        for i in range(0, len(test_rows), 16):
            batch = tok(
                [r['text'] for r in test_rows[i:i+16]],
                return_tensors='pt',
                padding=True,
                truncation=True,
                max_length=512
            ).to(device)
            p = torch.softmax(model(**batch).logits, dim=1).cpu().numpy()
            probs.extend(p)

    probs = np.array(probs)
    pred_ids = np.argmax(probs, axis=1)

    report = classification_report(gold_ids, pred_ids, target_names=LABELS, output_dict=True, zero_division=0)
    cm = confusion_matrix(gold_ids, pred_ids, labels=range(4))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'test_metrics.json').write_text(json.dumps(report, indent=2))
    np.save(out / 'test_probabilities.npy', probs)

    print("\n" + "="*50)
    print("GOLD TEST SPLIT EVALUATION (125 SAMPLES)")
    print("="*50)
    print(f"Accuracy:    {report['accuracy']:.4f}")
    print(f"Macro-F1:    {report['macro avg']['f1-score']:.4f}")
    print(f"Weighted-F1: {report['weighted avg']['f1-score']:.4f}")
    print("\nPer-class breakdown:")
    for k in LABELS:
        p = report[k]['precision']
        r = report[k]['recall']
        f = report[k]['f1-score']
        s = int(report[k]['support'])
        print(f"  {k:15}: Prec={p:.3f}, Recall={r:.3f}, F1={f:.3f} (support={s})")

    print("\nConfusion Matrix (Row=Gold, Col=Pred):")
    print(f"{'':15} " + " ".join(f"{k:>12}" for k in LABELS))
    for i, row_label in enumerate(LABELS):
        print(f"{row_label:15} " + " ".join(f"{cm[i, j]:12d}" for j in range(4)))

    return report, cm


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--model', default='models/roberta_curated/best')
    p.add_argument('--db', default='data/articles.db')
    p.add_argument('--out', default='results/curated')
    args = p.parse_args()
    evaluate_model(args.model, args.db, args.out)

