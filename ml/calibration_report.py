"""Generate test-only calibration, reliability, and coverage artifacts."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score
from training_common import LABEL_TO_ID, load_split

out=Path('results');out.mkdir(exist_ok=True)
rows=load_split('data/articles.db','test')
y=np.array([LABEL_TO_ID[r['label']] for r in rows])
p=np.load(out/'transformer_test_probabilities.npy')
t=json.loads(Path('models/best/temperature.json').read_text())['temperature']
log=np.log(np.clip(p,1e-8,1)); z=log/t; z-=z.max(1,keepdims=True); q=np.exp(z);q/=q.sum(1,keepdims=True)
def ece(prob):
 conf=prob.max(1);correct=(prob.argmax(1)==y); total=0.; bins=np.linspace(0,1,11)
 for lo,hi in zip(bins[:-1],bins[1:]):
  m=(conf>=lo)&((conf<hi) if hi<1 else (conf<=hi))
  if m.any(): total+=m.mean()*abs(correct[m].mean()-conf[m].mean())
 return total
report={'temperature':t,'uncalibrated_ece':ece(p),'calibrated_ece':ece(q),'coverage_vs_accuracy':[]}
for threshold in (.25,.35,.45,.55,.65,.75):
 keep=q.max(1)>=threshold
 report['coverage_vs_accuracy'].append({'threshold':threshold,'coverage':float(keep.mean()),'accuracy':float(accuracy_score(y[keep],q.argmax(1)[keep])) if keep.any() else None,'n':int(keep.sum())})
(out/'calibration_metrics.json').write_text(json.dumps(report,indent=2))
fig,ax=plt.subplots(figsize=(6,5));
for prob,name in ((p,'uncalibrated'),(q,'temperature-scaled')):
 xs=[];ys=[]
 for lo,hi in zip(np.linspace(0,1,11)[:-1],np.linspace(0,1,11)[1:]):
  m=(prob.max(1)>=lo)&(prob.max(1)<hi)
  if m.any():xs.append(prob.max(1)[m].mean());ys.append((prob.argmax(1)[m]==y[m]).mean())
 ax.plot(xs,ys,'o-',label=name)
ax.plot([0,1],[0,1],'k--');ax.set(xlabel='Confidence',ylabel='Accuracy',title='Gold test reliability');ax.legend();fig.tight_layout();fig.savefig(out/'reliability.png',dpi=160)
print(json.dumps(report,indent=2))
