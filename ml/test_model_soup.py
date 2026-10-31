"""Test Model Soup (weight averaging) between curated and focal RoBERTa models."""
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

m1_path = 'models/roberta_headline/best'
m2_path = 'models/roberta_curated/best'

print("Loading models for Weight Averaging (Model Soup)...")
tok = AutoTokenizer.from_pretrained(m1_path)
m1 = AutoModelForSequenceClassification.from_pretrained(m1_path).to(device)
m2 = AutoModelForSequenceClassification.from_pretrained(m2_path).to(device)

te = load_split('data/articles.db', 'test', headline_snippet_only=True)
gold_ids = [LABEL_TO_ID[r['label']] for r in te]

# Test alpha interpolations in weight space
for alpha in [0.0, 0.3, 0.5, 0.7, 1.0]:
    soup = copy.deepcopy(m1)
    state_soup = soup.state_dict()
    s1 = m1.state_dict()
    s2 = m2.state_dict()

    for k in state_soup.keys():
        state_soup[k] = (1.0 - alpha) * s1[k] + alpha * s2[k]

    soup.load_state_dict(state_soup)
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
    print(f"Soup Alpha (Curated)={alpha:.2f} -> Accuracy: {acc:.4f} | Macro-F1: {rep['macro avg']['f1-score']:.4f} | Weighted-F1: {rep['weighted avg']['f1-score']:.4f} | RIGHT-F1: {rep['RIGHT']['f1-score']:.3f} | NOT_POL-F1: {rep['NOT_POLITICAL']['f1-score']:.3f}")


