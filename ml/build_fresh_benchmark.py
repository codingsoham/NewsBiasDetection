"""Build an independent, out-of-distribution 40-article live benchmark from fresh Indian RSS feeds."""
from __future__ import annotations
import json
import re
from pathlib import Path
import feedparser

def clean_text(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

# Target live feeds
FEEDS = {
    'opindia': 'https://www.opindia.com/feed/',
    'organiser': 'https://organiser.org/feed/',
    'thewire': 'https://news.google.com/rss/search?q=site:thewire.in&hl=en-IN&gl=IN&ceid=IN:en',
    'swarajya': 'https://news.google.com/rss/search?q=site:swarajyamag.com&hl=en-IN&gl=IN&ceid=IN:en',
    'thehindu': 'https://www.thehindu.com/news/national/feeder/default.rss',
    'express_pol': 'https://indianexpress.com/section/politics/feed/',
    'express_sports': 'https://indianexpress.com/section/sports/feed/',
    'express_tech': 'https://indianexpress.com/section/technology/feed/'
}

print("Fetching fresh live feeds...")
entries = {}
for key, url in FEEDS.items():
    try:
        f = feedparser.parse(url)
        entries[key] = f.entries
        print(f"  {key:15}: {len(f.entries)} articles fetched")
    except Exception as e:
        print(f"  {key:15}: Error {e}")
        entries[key] = []

benchmark_items = []

# 1. Ten Curated RIGHT Articles (From Swarajya, Organiser, OpIndia)
right_candidates = []
for k in ['organiser', 'opindia', 'swarajya']:
    for e in entries.get(k, []):
        t = clean_text(e.title)
        s = clean_text(e.get('summary', ''))
        # Avoid non-political or pure civic
        if any(w in t.lower() for w in ['modi', 'bjp', 'govt', 'hindutva', 'deal', 'rss', 'congress', 'opposition', 'pakistan', 'rahul', 'national']):
            right_candidates.append({
                'source': 'Organiser' if k == 'organiser' else ('OpIndia' if k == 'opindia' else 'Swarajya'),
                'title': t,
                'snippet': s[:200],
                'label': 'RIGHT',
                'justification': 'Framing emphasizes national security/governance achievements, Hindu cultural advocacy, or critical scrutiny of opposition.'
            })

# 2. Ten Curated LEFT Articles (From The Wire)
left_candidates = []
for e in entries.get('thewire', []):
    t = clean_text(e.title)
    s = clean_text(e.get('summary', ''))
    if any(w in t.lower() for w in ['bjp', 'ec', 'modi', 'protest', 'clampdown', 'cbi', 'rights', 'infiltrators', 'arrest', 'investigation', 'adulteration']):
        left_candidates.append({
            'source': 'The Wire',
            'title': t,
            'snippet': s[:200],
            'label': 'LEFT',
            'justification': 'Critical institutional watchdog framing, civil liberties focus, or scrutiny of ruling government actions.'
        })

# 3. Ten Curated CENTER Articles (From The Hindu, Indian Express Politics)
center_candidates = []
for k in ['thehindu', 'express_pol']:
    for e in entries.get(k, []):
        t = clean_text(e.title)
        s = clean_text(e.get('summary', ''))
        # Must be political/policy but balanced or procedural
        if any(w in t.lower() for w in ['court', 'minister', 'parliament', 'assembly', 'cabinet', 'orders', 'status quo', 'gdp', 'gandhi', 'talks', 'bill']):
            center_candidates.append({
                'source': 'The Hindu' if k == 'thehindu' else 'Indian Express',
                'title': t,
                'snippet': s[:200],
                'label': 'CENTER',
                'justification': 'Neutral, procedural reporting of official announcements, court orders, or balanced attribution of competing claims.'
            })

# 4. Ten Curated NOT_POLITICAL Articles (Sports, Tech, Local incidents)
not_pol_candidates = []
for k in ['express_sports', 'express_tech', 'thehindu']:
    for e in entries.get(k, []):
        t = clean_text(e.title)
        s = clean_text(e.get('summary', ''))
        # Must be pure sports/tech/crime without politics
        if any(w in t.lower() for w in ['chess', 'cricket', 'pragg', 'sindarov', 'smartphone', 'review', 'apple', 'google', 'chocolate', 'kills four-year-old', 'match', 'ipl', 'medal']):
            not_pol_candidates.append({
                'source': 'Indian Express' if 'express' in k else 'The Hindu',
                'title': t,
                'snippet': s[:200],
                'label': 'NOT_POLITICAL',
                'justification': 'Routine non-political coverage of sports, technology, or non-political local crime.'
            })

# Select exactly 10 per class (deduplicated by title)
def select_unique(cand_list, n=10):
    seen = set()
    out = []
    for c in cand_list:
        if c['title'] not in seen:
            seen.add(c['title'])
            out.append(c)
            if len(out) == n:
                break
    return out

final_benchmark = (
    select_unique(right_candidates, 10) +
    select_unique(left_candidates, 10) +
    select_unique(center_candidates, 10) +
    select_unique(not_pol_candidates, 10)
)

print(f"\nFinal Benchmark Created: Total {len(final_benchmark)} articles:")
counts = {}
for item in final_benchmark:
    counts[item['label']] = counts.get(item['label'], 0) + 1
print(counts)

out_file = Path('data/fresh_live_benchmark_2026.json')
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(json.dumps(final_benchmark, indent=2), encoding='utf-8')
print(f"Saved benchmark to {out_file}!")

