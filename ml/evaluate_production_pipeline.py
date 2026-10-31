"""Comprehensive evaluation of the active production pipeline (Option 1 + Sanitizer + SAT & Trailing Attribution Resolver)
across both the Held-Out Gold Test Set (90 items) and the Live 2026 Benchmark (40 items).
"""
import json
import sqlite3
import sys
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import predict_batch
from ml.training_common import LABELS, LABEL_TO_ID, load_split

def eval_gold_test_set():
    print("=" * 60)
    print("1. EVALUATING HELD-OUT GOLD TEST SET")
    print("=" * 60)
    rows = load_split('data/articles.db', 'test', head_tail=False, headline_snippet_only=True)
    print(f"Loaded {len(rows)} gold test samples.")
    
    texts = [r['text'] for r in rows]
    sources = [r.get('source') for r in rows]
    gold_labels = [r['label'] for r in rows]
    gold_ids = [LABEL_TO_ID[l] for l in gold_labels]
    
    # Run through production pipeline
    predictions = predict_batch(texts, sources=sources, batch_size=32)
    pred_labels = [max(p, key=p.get) for p in predictions]
    pred_ids = [LABEL_TO_ID[l] for l in pred_labels]
    
    acc = accuracy_score(gold_ids, pred_ids)
    rep = classification_report(gold_ids, pred_ids, target_names=LABELS, output_dict=True, zero_division=0)
    cm = confusion_matrix(gold_ids, pred_ids, labels=range(4))
    
    print(f"Accuracy:    {acc:.4f} ({np.sum(np.array(gold_ids) == np.array(pred_ids))}/{len(gold_ids)} correct)")
    print(f"Macro-F1:    {rep['macro avg']['f1-score']:.4f}")
    print(f"Weighted-F1: {rep['weighted avg']['f1-score']:.4f}")
    print("\nPer-Class Breakdown:")
    for l in LABELS:
        print(f"  {l:15}: Prec={rep[l]['precision']:.3f}, Rec={rep[l]['recall']:.3f}, F1={rep[l]['f1-score']:.3f} (support={int(rep[l]['support'])})")
        
    print("\nConfusion Matrix (Row=Gold, Col=Pred):")
    header = f"{'':15}" + "".join(f"{l:>15}" for l in LABELS)
    print(header)
    for i, row in enumerate(cm):
        print(f"{LABELS[i]:15}" + "".join(f"{val:>15}" for val in row))
        
    return acc, rep, cm

def eval_live_benchmark():
    print("\n" + "=" * 60)
    print("2. EVALUATING LIVE 2026 RSS BENCHMARK (40 ITEMS)")
    print("=" * 60)
    items = json.loads(Path('data/fresh_live_benchmark_2026.json').read_text(encoding='utf-8'))
    print(f"Loaded {len(items)} fresh benchmark articles.")
    
    texts = [f"{item['title']} {item['snippet']}" for item in items]
    sources = [item['source'] for item in items]
    gold_labels = [item['label'] for item in items]
    gold_ids = [LABEL_TO_ID[l] for l in gold_labels]
    
    predictions = predict_batch(texts, sources=sources, batch_size=32)
    pred_labels = [max(p, key=p.get) for p in predictions]
    pred_ids = [LABEL_TO_ID[l] for l in pred_labels]
    
    acc = accuracy_score(gold_ids, pred_ids)
    rep = classification_report(gold_ids, pred_ids, target_names=LABELS, output_dict=True, zero_division=0)
    cm = confusion_matrix(gold_ids, pred_ids, labels=range(4))
    
    print(f"Accuracy:    {acc:.4f} ({np.sum(np.array(gold_ids) == np.array(pred_ids))}/{len(gold_ids)} correct)")
    print(f"Macro-F1:    {rep['macro avg']['f1-score']:.4f}")
    print(f"Weighted-F1: {rep['weighted avg']['f1-score']:.4f}")
    print("\nPer-Class Breakdown:")
    for l in LABELS:
        print(f"  {l:15}: Prec={rep[l]['precision']:.3f}, Rec={rep[l]['recall']:.3f}, F1={rep[l]['f1-score']:.3f} (support={int(rep[l]['support'])})")
        
    print("\nConfusion Matrix (Row=Gold, Col=Pred):")
    header = f"{'':15}" + "".join(f"{l:>15}" for l in LABELS)
    print(header)
    for i, row in enumerate(cm):
        print(f"{LABELS[i]:15}" + "".join(f"{val:>15}" for val in row))
        
    return acc, rep, cm

if __name__ == '__main__':
    eval_gold_test_set()
    eval_live_benchmark()

