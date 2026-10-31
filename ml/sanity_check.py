"""Smoke test inference and warn on single-class collapse."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import predict_text
SAMPLES={'LEFT':'Civil society groups said the government action threatens minority rights.','CENTER':'The court listed the case for hearing next week and sought replies.','RIGHT':'The government described the reform as a decisive national achievement.','NOT_POLITICAL':'The team won the cricket match by five wickets.'}
labels=[]
for expected,text in SAMPLES.items():
 p=predict_text(text);label=max(p,key=p.get);labels.append(label);print(expected,label,round(p[label],3))
if max(labels.count(x) for x in set(labels))/len(labels)>.95: raise SystemExit('FAIL: single-class collapse')
print('PASS: no single-class collapse')
