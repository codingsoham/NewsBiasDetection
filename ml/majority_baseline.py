"""Evaluate the training-set majority label on the locked gold test set."""
import json
from pathlib import Path
from sklearn.metrics import classification_report
from training_common import LABELS,load_split
tr,te=load_split('data/articles.db','train'),load_split('data/articles.db','test');majority=max(LABELS,key=lambda x:sum(r['label']==x for r in tr));r=classification_report([x['label'] for x in te],[majority]*len(te),labels=list(LABELS),output_dict=True,zero_division=0);r['majority_label']=majority;Path('results/majority_metrics.json').write_text(json.dumps(r,indent=2));print(json.dumps({'majority_label':majority,'accuracy':r['accuracy'],'macro_f1':r['macro avg']['f1-score']},indent=2))
