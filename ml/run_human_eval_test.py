"""Run production model inference on the 5 user-evaluated headlines."""
from __future__ import annotations
import json
import urllib.request

test_cases = [
    {
        'num': 1,
        'source': 'Organiser',
        'title': 'Big boost to Indian Naval Power: Modi Govt clears Rs 40,000 crore deal for 8 next-gen warships, first delivery by 2030',
        'user_label': 'mostly centre little leaning to right'
    },
    {
        'num': 2,
        'source': 'The Wire',
        'title': 'BJP and EC Said SIR Was to Remove Infiltrators. A Report Shows it Recorded Just 1,600 Foreigners',
        'user_label': 'mostly centre little left not much'
    },
    {
        'num': 3,
        'source': 'The Hindu',
        'title': 'IRCTC hotels case: Delhi court defers formal framing of charges against Lalu Prasad and Tejashwi Yadav to Dec 10',
        'user_label': 'mostly centre'
    },
    {
        'num': 4,
        'source': 'Indian Express',
        'title': "Final-day drama: Sindarov overturns Pragg's lead to claim Clutch Chess crown",
        'user_label': 'non political'
    },
    {
        'num': 5,
        'source': 'The Wire',
        'title': 'Congress lashes out at BJP over draconian law in parliament, calls it murder of democracy',
        'user_label': 'tie between left and centre but little more left'
    }
]

print("="*70)
print("RUNNING PRODUCTION MODEL PREDICTIONS ON USER TEST HEADLINES")
print("="*70)

results = []
for c in test_cases:
    payload = json.dumps({'text': c['title'], 'source': c['source']}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/predict', data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
    
    p = res['probabilities']
    loaded = [x['term'] for x in res['explanation'].get('loaded_terms', [])]
    rat = res['explanation'].get('rationale', '')

    results.append({
        'num': c['num'],
        'source': c['source'],
        'title': c['title'],
        'user_label': c['user_label'],
        'pred_label': res['label'],
        'probs': p,
        'loaded_terms': loaded,
        'rationale': rat
    })

print(json.dumps(results, indent=2))

