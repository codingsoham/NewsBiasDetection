"""Evaluate the three-class Stage-1 model on political items in the Indian gold test set.

NOT_POLITICAL is intentionally excluded because Stage 1 has no such output class.
"""
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report
from training_common import load_split

LABELS=('LEFT','CENTER','RIGHT')
def main():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    rows=[r for r in load_split('data/articles.db','test') if r['label'] in LABELS]
    path='models/baly_stage1/best'; tok=AutoTokenizer.from_pretrained(path)
    model=AutoModelForSequenceClassification.from_pretrained(path).eval()
    out=[]
    with torch.no_grad():
        for i in range(0,len(rows),16):
            batch=tok([r['text'] for r in rows[i:i+16]],return_tensors='pt',padding=True,truncation=True,max_length=512)
            out.extend(model(**batch).logits.argmax(1).tolist())
    y=[LABELS.index(r['label']) for r in rows]
    report=classification_report(y,out,labels=range(3),target_names=LABELS,output_dict=True,zero_division=0)
    report['scope']='Political-only Indian gold test; NOT_POLITICAL excluded because Stage 1 is three-class.'
    report['n']=len(rows)
    Path('results/stage1_indian_political_test_metrics.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'n':len(rows),'accuracy':report['accuracy'],'macro_f1':report['macro avg']['f1-score']},indent=2))
if __name__=='__main__':main()
