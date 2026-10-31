"""Fit scalar temperature on gold validation probabilities and save it for serving."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.optimize import minimize_scalar
from training_common import LABEL_TO_ID,load_split
from backend.app import predict_text
rows=load_split('data/articles.db','validation');p=np.array([[predict_text(r['text'])[x] for x in ('LEFT','CENTER','RIGHT','NOT_POLITICAL')] for r in rows]);y=np.array([LABEL_TO_ID[r['label']] for r in rows]);log=np.log(np.clip(p,1e-8,1));
def nll(t):
 z=log/t;z-=z.max(1,keepdims=True);q=np.exp(z);q/=q.sum(1,keepdims=True);return -np.log(q[np.arange(len(y)),y]).mean()
t=float(minimize_scalar(nll,bounds=(.25,5),method='bounded').x);Path('models/best/temperature.json').write_text(json.dumps({'temperature':t,'validation_nll':nll(t)},indent=2));print(t,nll(t))
