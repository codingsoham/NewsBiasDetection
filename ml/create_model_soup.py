"""Create, calibrate, evaluate, and save the 50/50 Model Soup RoBERTa model."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import sys
sys.path.append('ml')
from training_common import load_split, LABEL_TO_ID, LABELS

device = 'cuda' if torch.cuda.is_available() else 'cpu'

m1_path = 'models/roberta_headline/best'
m2_path = 'models/roberta_curated/best'
out_dir = Path('models/soup/best')
out_dir.mkdir(parents=True, exist_ok=True)

print("Constructing 50/50 Model Soup from Focal + Curated RoBERTa checkpoints...")
tok = AutoTokenizer.from_pretrained(m1_path)
m1 = AutoModelForSequenceClassification.from_pretrained(m1_path).to(device)
m2 = AutoModelForSequenceClassification.from_pretrained(m2_path).to(device)

soup = copy.deepcopy(m1)
state_soup = soup.state_dict()
s1 = m1.state_dict()
s2 = m2.state_dict()

for k in state_soup.keys():
    state_soup[k] = 0.5 * s1[k] + 0.5 * s2[k]

soup.load_state_dict(state_soup)
soup.eval()

# Save Model Soup
print(f"Saving Model Soup weights and tokenizer to {out_dir}...")
soup.save_pretrained(str(out_dir))
tok.save_pretrained(str(out_dir))

# Evaluate on Validation split to calibrate temperature
val_rows = load_split('data/articles.db', 'validation', headline_snippet_only=True)
val_gold = [LABEL_TO_ID[r['label']] for r in val_rows]

val_logits = []
with torch.no_grad():
    for i in range(0, len(val_rows), 16):
        batch = tok([r['text'] for r in val_rows[i:i+16]], return_tensors='pt', padding=True, truncation=True, max_length=512).to(device)
        l = soup(**batch).logits.cpu().numpy()
        val_logits.extend(l)

val_logits = torch.tensor(np.array(val_logits))
val_labels = torch.tensor(val_gold)

# Optimize temperature scaling
t_param = torch.nn.Parameter(torch.ones(1) * 1.2)
opt = torch.optim.LBFGS([t_param], lr=0.01, max_iter=50)

def eval_nll():
    opt.zero_grad()
    loss = torch.nn.functional.cross_entropy(val_logits / t_param, val_labels)
    loss.backward()
    return loss

opt.step(eval_nll)
optimal_t = float(t_param.item())
print(f"Optimal Temperature on Validation: T = {optimal_t:.4f}")

# Save temperature
(out_dir / 'temperature.json').write_text(json.dumps({'temperature': optimal_t, 'method': 'validation_nll'}, indent=2))

# Evaluate on Gold Test Split
te_rows = load_split('data/articles.db', 'test', headline_snippet_only=True)
gold_ids = [LABEL_TO_ID[r['label']] for r in te_rows]

test_probs = []
with torch.no_grad():
    for i in range(0, len(te_rows), 16):
        batch = tok([r['text'] for r in te_rows[i:i+16]], return_tensors='pt', padding=True, truncation=True, max_length=512).to(device)
        p = torch.softmax(soup(**batch).logits / optimal_t, dim=1).cpu().numpy()
        test_probs.extend(p)

test_probs = np.array(test_probs)
preds = np.argmax(test_probs, axis=1)

rep = classification_report(gold_ids, preds, target_names=LABELS, output_dict=True, zero_division=0)
cm = confusion_matrix(gold_ids, preds, labels=range(4))

res_dir = Path('results/soup')
res_dir.mkdir(parents=True, exist_ok=True)
(res_dir / 'test_metrics.json').write_text(json.dumps(rep, indent=2))
np.save(res_dir / 'test_probabilities.npy', test_probs)

print("\n" + "="*50)
print("MODEL SOUP GOLD TEST EVALUATION")
print("="*50)
print(f"Accuracy:    {accuracy_score(gold_ids, preds):.4f}")
print(f"Macro-F1:    {rep['macro avg']['f1-score']:.4f}")
print(f"Weighted-F1: {rep['weighted avg']['f1-score']:.4f}")

print("\nPer-Class Breakdown:")
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

