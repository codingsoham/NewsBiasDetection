"""Evaluate our active production model against the 40-article fresh live Indian benchmark."""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

LABELS = ['LEFT', 'CENTER', 'RIGHT', 'NOT_POLITICAL']
LABEL_TO_ID = {l: i for i, l in enumerate(LABELS)}

benchmark_file = Path('data/fresh_live_benchmark_2026.json')
items = json.loads(benchmark_file.read_text(encoding='utf-8'))

print(f"Loaded {len(items)} fresh benchmark articles.")

gold_labels = [item['label'] for item in items]
gold_ids = [LABEL_TO_ID[l] for l in gold_labels]

pred_labels = []
pred_probs = []
details = []

print("\nRunning inference via live production FastAPI service (http://127.0.0.1:8000/predict)...")

for idx, item in enumerate(items, 1):
    text = f"{item['title']} {item['snippet']}"
    payload = json.dumps({'text': text, 'source': item['source']}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/predict', data=payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            probs = res['probabilities']
            # Raw 4-way classification decision is the argmax of probabilities
            top_pred = max(probs, key=probs.get)
            is_unclear = (res['label'] == 'UNCLEAR')
            loaded = [x['term'] for x in res['explanation'].get('loaded_terms', [])]
            rat = res['explanation'].get('rationale', '')
    except Exception as e:
        print(f"Error on item {idx}: {e}")
        probs = {'LEFT': 0.25, 'CENTER': 0.25, 'RIGHT': 0.25, 'NOT_POLITICAL': 0.25}
        top_pred = 'CENTER'
        is_unclear = True
        loaded, rat = [], 'Error'

    pred_labels.append(top_pred)
    pred_probs.append(probs)

    match = (top_pred == item['label'])
    details.append({
        'id': idx,
        'source': item['source'],
        'title': item['title'],
        'gold': item['label'],
        'pred': top_pred,
        'is_unclear': is_unclear,
        'match': match,
        'probabilities': probs,
        'loaded_terms': loaded,
        'rationale': rat
    })

pred_ids = [LABEL_TO_ID[l] for l in pred_labels]

acc = accuracy_score(gold_ids, pred_ids)
report = classification_report(gold_ids, pred_ids, target_names=LABELS, output_dict=True, zero_division=0)
cm = confusion_matrix(gold_ids, pred_ids, labels=range(4))

out_res = {
    'total_samples': len(items),
    'accuracy': acc,
    'macro_f1': report['macro avg']['f1-score'],
    'weighted_f1': report['weighted avg']['f1-score'],
    'per_class': {k: report[k] for k in LABELS},
    'confusion_matrix': cm.tolist(),
    'items': details
}

Path('results/live_benchmark_eval.json').write_text(json.dumps(out_res, indent=2), encoding='utf-8')

print("\n" + "="*60)
print("OUT-OF-DISTRIBUTION LIVE INDIAN BENCHMARK RESULTS (40 SAMPLES)")
print("="*60)
print(f"Accuracy:    {acc:.4f} ({int(acc*len(items))}/{len(items)} correct)")
print(f"Macro-F1:    {report['macro avg']['f1-score']:.4f}")
print(f"Weighted-F1: {report['weighted avg']['f1-score']:.4f}")

print("\nPer-Class Metrics:")
for k in LABELS:
    p = report[k]['precision']
    r = report[k]['recall']
    f = report[k]['f1-score']
    s = int(report[k]['support'])
    print(f"  {k:15}: Prec={p:.3f}, Recall={r:.3f}, F1={f:.3f} (support={s})")

print("\nConfusion Matrix (Row=Gold, Col=Predicted):")
print(f"{'':15} " + " ".join(f"{k:>12}" for k in LABELS))
for i, row_label in enumerate(LABELS):
    print(f"{row_label:15} " + " ".join(f"{cm[i, j]:12d}" for j in range(4)))

print("\nDiscrepancies (Misclassified items):")
for d in details:
    if not d['match']:
        t = d['title'][:60].encode('ascii', 'ignore').decode()
        print(f"  Item #{d['id']:2d} [{d['source']}]: Gold={d['gold']:13} -> Pred={d['pred']:13} | {t}")
