"""Evaluate a saved classifier only on the Phase 3 gold test split."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report,confusion_matrix
from training_common import LABELS,LABEL_TO_ID,load_split
def main():
 p=argparse.ArgumentParser();p.add_argument('--model',default='models/best/best');p.add_argument('--db',default='data/articles.db');p.add_argument('--out',default='results');p.add_argument('--head-tail',action='store_true');p.add_argument('--name',default='transformer');a=p.parse_args()
 import torch
 from transformers import AutoModelForSequenceClassification,AutoTokenizer
 rows=load_split(a.db,'test',a.head_tail);tok=AutoTokenizer.from_pretrained(a.model);m=AutoModelForSequenceClassification.from_pretrained(a.model).to('cuda' if torch.cuda.is_available() else 'cpu').eval();device=next(m.parameters()).device
 probs=[]
 with torch.no_grad():
  for i in range(0,len(rows),16):
   batch=tok([r['text'] for r in rows[i:i+16]],return_tensors='pt',padding=True,truncation=True,max_length=512).to(device);probs.extend(torch.softmax(m(**batch).logits,dim=1).cpu().numpy())
 y=np.array([LABEL_TO_ID[r['label']] for r in rows]);pred=np.argmax(probs,axis=1);report=classification_report(y,pred,target_names=LABELS,output_dict=True,zero_division=0);cm=confusion_matrix(y,pred,labels=range(4));out=Path(a.out);out.mkdir(exist_ok=True);(out/f'{a.name}_test_metrics.json').write_text(json.dumps(report,indent=2));np.save(out/f'{a.name}_test_probabilities.npy',np.array(probs))
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,6));im=ax.imshow(cm,cmap='Blues');ax.set(xticks=range(4),yticks=range(4),xticklabels=LABELS,yticklabels=LABELS,xlabel='Predicted',ylabel='Gold',title='Gold test confusion matrix');plt.setp(ax.get_xticklabels(),rotation=35,ha='right')
 for i in range(4):
  for j in range(4):ax.text(j,i,str(cm[i,j]),ha='center',va='center')
 fig.colorbar(im);fig.tight_layout();fig.savefig(out/f'{a.name}_confusion_matrix.png',dpi=160);print(json.dumps({'accuracy':report['accuracy'],'macro_f1':report['macro avg']['f1-score']},indent=2))
if __name__=='__main__':main()
