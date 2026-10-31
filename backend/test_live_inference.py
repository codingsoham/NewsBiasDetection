"""Test live model inference on diverse inputs."""
from __future__ import annotations
import urllib.request
import json

def test_pred(text, src):
    data = json.dumps({'text': text, 'source': src}).encode()
    req = urllib.request.Request('http://127.0.0.1:8000/predict', data=data, headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    print(f"\n[{src}] {text}")
    print(f"  --> Predicted: {res['label']}")
    print(f"  --> Probabilities: {res['probabilities']}")
    if res['explanation']['loaded_terms']:
        print(f"  --> Loaded Terms: {[x['term'] for x in res['explanation']['loaded_terms']]}")
    print(f"  --> Rationale: {res['explanation']['rationale']}")

print("="*60)
print("LIVE MODEL INFERENCE VERIFICATION (PRODUCTION-READY MODEL)")
print("="*60)
test_pred("Virat Kohli scores brilliant 100 as India wins 3rd T20I match against New Zealand", "Indian Express")
test_pred("Supreme Court reserves verdict on constitutional validity of Waqf amendment bill", "The Hindu")
test_pred("Congress lashes out at BJP over draconian law in parliament, calls it murder of democracy", "The Wire")
test_pred("Historic masterstroke: Modi government transforms connectivity with 322 km expressway network", "Swarajya")

