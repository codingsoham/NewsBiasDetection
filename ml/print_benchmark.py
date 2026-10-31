"""Print all 40 fresh benchmark items."""
import json

data = json.load(open('data/fresh_live_benchmark_2026.json', encoding='utf-8'))
for i, item in enumerate(data, 1):
    t = item['title'][:70].encode('ascii', 'ignore').decode()
    lbl = item['label']
    src = item['source']
    print(f"{i:2d}. [{lbl:13}] [{src:14}] {t}")

