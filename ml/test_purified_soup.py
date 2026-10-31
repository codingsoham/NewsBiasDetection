"""Test Model Soup combinations with roberta_purified."""
from __future__ import annotations
import copy
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import sys
sys.path.append('ml')
from training_common import load_split, LABEL_TO_ID, LABELS

device = 'cuda' if torch.cuda.is_available() else 'cpu'

m_purified_path = 'models/roberta_purified/best'
m_focal_path = 'models/roberta_headline/best'

tok = AutoTokenizer.from_pretrained(m_purified_path)
m_purified = AutoModelForSequenceClassification.from_pretrained(m_purified_path).to(device)
m_focal = AutoModelForSequenceClassification.from_pretrained(m_focal_path).to(device)

te = load_split('data/articles.db', 'test', headline_snippet_only=True)
gold_ids = [LABEL_TO_ID[r['label']] for r in te]

print("Evaluating Weight Interpolations: Purified vs Focal")
for alpha_focal in [0.0, 0.15, 0.25, 0.35, 0.50]:
    soup = copy.deepcopy(m_purified)
    state = soup.state_dict()
    sp = m_purified.state_dict()
    sf = m_focal.state_dict()

    for k in state.keys():
        state[k] = (1.0 - alpha_focal) * sp[k] + alpha_focal * sf[k]

    soup.load_state_dict(state)
    soup.eval()

    probs = []
    with torch.no_grad():
        for i in range(0, len(te), 16):
            batch = tok([r['text'] for r in te[i:i+16]], return_tensors='pt', padding=True, truncation=True, max_length=512).to(device)
            p = torch.softmax(soup(**batch).logits, dim=1).cpu().numpy()
            probs.extend(p)

    preds = np.argmax(probs, axis=1)
    acc = accuracy_score(gold_ids, preds)
    rep = classification_report(gold_ids, preds, target_names=LABELS, output_dict=True, zero_division=0)
    print(f"Alpha Focal={alpha_focal:.2f} -> Accuracy: {acc:.4f} | Macro-F1: {rep['macro avg']['f1-score']:.4f} | Weighted-F1: {rep['weighted avg']['f1-score']:.4f} | RIGHT-F1: {rep['RIGHT']['f1-score']:.3f} | NOT_POL-F1: {rep['NOT_POLITICAL']['f1-score']:.3f}")

