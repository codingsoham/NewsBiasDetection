"""Test fetching live Indian feeds."""
import feedparser

FEEDS = [
    ('OpIndia', 'https://www.opindia.com/feed/'),
    ('Organiser', 'https://organiser.org/feed/'),
    ('The Hindu', 'https://www.thehindu.com/news/national/feeder/default.rss'),
    ('Indian Express Politics', 'https://indianexpress.com/section/politics/feed/'),
    ('Indian Express Sports', 'https://indianexpress.com/section/sports/feed/'),
    ('Google News The Wire', 'https://news.google.com/rss/search?q=site:thewire.in&hl=en-IN&gl=IN&ceid=IN:en'),
    ('Google News Swarajya', 'https://news.google.com/rss/search?q=site:swarajyamag.com&hl=en-IN&gl=IN&ceid=IN:en')
]

for name, url in FEEDS:
    try:
        f = feedparser.parse(url)
        print(f"[{name}] Fetched {len(f.entries)} live articles.")
        if f.entries:
            t = f.entries[0].title.encode('ascii', 'ignore').decode()
            print(f"   Sample: {t[:70]}")
    except Exception as e:
        print(f"[{name}] Error: {e}")

