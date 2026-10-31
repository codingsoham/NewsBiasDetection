"""Report outlet-prior blending without leaking held-out publisher labels.

The Phase 3 split holds NDTV and India Today out entirely.  Consequently their
outlet-specific priors do not exist at training time and correctly fall back to
the global train prior; this report makes that limitation measurable.
"""
import json, sqlite3
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from training_common import LABELS, LABEL_TO_ID

def score(y, probs):
    pred=probs.argmax(1)
    return {'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1_score(y,pred,average='macro',zero_division=0))}

def main():
    db=sqlite3.connect('data/articles.db'); db.row_factory=sqlite3.Row
    train=db.execute("""select a.source,d.label from dataset_splits d join articles a on a.id=d.article_id where d.split='train'""").fetchall()
    test=db.execute("""select a.source,d.label from dataset_splits d join articles a on a.id=d.article_id where d.split='test' order by a.id""").fetchall()
    counts=np.bincount([LABEL_TO_ID[r['label']] for r in train],minlength=4).astype(float)
    global_prior=counts/counts.sum(); per={}
    for source in {r['source'] for r in train}:
        values=[LABEL_TO_ID[r['label']] for r in train if r['source']==source]
        per[source]=np.bincount(values,minlength=4)/len(values)
    model=np.load('results/transformer_test_probabilities.npy'); y=np.array([LABEL_TO_ID[r['label']] for r in test])
    priors=np.array([per.get(r['source'],global_prior) for r in test])
    report={'scope':'Gold held-out test. Unseen publishers use global train prior; no test labels are used.',
            'unseen_test_sources':sorted({r['source'] for r in test if r['source'] not in per}),
            'model_only':score(y,model),'prior_only':score(y,priors),
            'model_plus_prior_50_50':score(y,(model+priors)/2)}
    Path('results/outlet_prior_report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
if __name__=='__main__':main()
