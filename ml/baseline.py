"""Train leakage-safe TF-IDF logistic-regression and majority baselines."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from training_common import LABELS,load_split

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',default='data/articles.db');p.add_argument('--out',default='results');a=p.parse_args()
 tr,te=load_split(a.db,'train'),load_split(a.db,'test')
 v=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=60000,sublinear_tf=True)
 x=v.fit_transform([r['text'] for r in tr]); xt=v.transform([r['text'] for r in te])
 y=[r['label'] for r in tr]; yt=[r['label'] for r in te]
 m=LogisticRegression(max_iter=2000,class_weight='balanced',random_state=42).fit(x,y)
 report=classification_report(yt,m.predict(xt),labels=list(LABELS),output_dict=True,zero_division=0)
 out=Path(a.out);out.mkdir(exist_ok=True);(out/'tfidf_metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps({'accuracy':report['accuracy'],'macro_f1':report['macro avg']['f1-score']},indent=2))
if __name__=='__main__':main()
