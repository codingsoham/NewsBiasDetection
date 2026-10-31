"""Evaluate the requested public pretrained political-bias model on locked gold test data."""
import json
from pathlib import Path
from transformers import pipeline
from sklearn.metrics import classification_report
from training_common import LABELS,load_split
rows=load_split('data/articles.db','test')
clf=pipeline('text-classification',model='peekayitachi/roberta-political-bias',truncation=True,max_length=512)
raw=clf([r['text'] for r in rows],batch_size=16)
def norm(x):
 x=x.upper().replace('-','_').replace(' ','_')
 if x in {'LABEL_0','LEFT'}:return 'LEFT'
 if x in {'LABEL_1','CENTER','CENTRE'}:return 'CENTER'
 if x in {'LABEL_2','RIGHT'}:return 'RIGHT'
 return x
pred=[norm(x['label']) for x in raw]
if any(x not in LABELS for x in pred):raise SystemExit(f'Unsupported pretrained labels: {sorted(set(pred))}')
r=classification_report([x['label'] for x in rows],pred,labels=list(LABELS),output_dict=True,zero_division=0);r['model']='peekayitachi/roberta-political-bias';Path('results/pretrained_metrics.json').write_text(json.dumps(r,indent=2));print(json.dumps({'accuracy':r['accuracy'],'macro_f1':r['macro avg']['f1-score']},indent=2))
