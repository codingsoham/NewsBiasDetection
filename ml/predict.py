"""Return experimental classifier probabilities for one text without exposing training data."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import predict_text
def main():
 p=argparse.ArgumentParser();p.add_argument('text');p.add_argument('--threshold',type=float,default=.45);a=p.parse_args();probs=predict_text(a.text);top=max(probs,key=probs.get);print(json.dumps({'label':top if probs[top]>=a.threshold else 'UNCLEAR','probabilities':probs,'low_confidence':probs[top]<a.threshold,'warning':'Experimental AI estimate; may be wrong.'},indent=2))
if __name__=='__main__':main()
