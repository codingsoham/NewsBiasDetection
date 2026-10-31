"""Text cleaning and normalization for fair, un-watermarked bias evaluation.
Strips publisher watermarks, Google News aggregator artifacts, HTML entities,
and redundant title duplications so RoBERTa evaluates pure journalistic prose.
"""
from __future__ import annotations

import html
import re

# Comprehensive list of Indian and international publisher names, domains, and wire services
KNOWN_PUBLISHERS = [
    r'Scroll(?:\.in)?',
    r'TheWire(?:\.in)?',
    r'The Wire',
    r'Bar and Bench',
    r'Live\s*Law',
    r'Live\s*Mint',
    r'Livemint',
    r'The Hindu',
    r'The Indian Express',
    r'Indian Express',
    r'Hindustan Times',
    r'The Times of India',
    r'Times of India',
    r'NDTV',
    r'ThePrint',
    r'theprint',
    r'India Today',
    r'OpIndia',
    r'Swarajya',
    r'Organiser(?:\s*Weekly)?',
    r'Firstpost',
    r'Deccan Herald',
    r'Deccan Chronicle',
    r'The Quint',
    r'Frontline Magazine',
    r'The Statesman',
    r'The Tribune',
    r'Free Press Journal',
    r'ANI News',
    r'ANI',
    r'PTI',
    r'Press Trust of India',
    r'Reuters',
    r'Bloomberg(?:\.com)?',
    r'Business Standard',
    r'Business Today',
    r'CNBC TV18',
    r'ETV Bharat',
    r'Telegraph India',
    r'National Herald',
    r'DNA India',
    r'Mathrubhumi English',
    r'News18',
    r'ABP Live(?:\s*English)?',
    r'Outlook India',
    r'The Economic Times',
    r'Financial Express',
    r'BBC',
    r'Al Jazeera',
    r'Dhaka Tribune'
]

# Pattern matching publisher signatures at the end of text or preceded by common separators
# Examples: '&nbsp;&nbsp; Scroll.in', '- The Hindu', '| NDTV', '— Bar and Bench'
_PUB_OR = '|'.join(KNOWN_PUBLISHERS)
TRAILING_WATERMARK_RE = re.compile(
    r'(?:\s*[-|•–—/]\s*|\s*&nbsp;\s*|\s{2,})(?:' + _PUB_OR + r')(?:\.com|\.in|\.org)?\s*$',
    re.IGNORECASE
)

# Pattern for inline publisher tags within Google News lists, e.g. '&nbsp;&nbsp; NDTV'
INLINE_WATERMARK_RE = re.compile(
    r'(?:&nbsp;|\s)+(?:[-|•–—/]\s*)?(?:' + _PUB_OR + r')(?:\.com|\.in|\.org)?(?:\s*[-|•–—/])?(?:&nbsp;|\s)*',
    re.IGNORECASE
)


def unescape_text(text: str | None) -> str:
    """Decode HTML entities and normalize whitespace."""
    if not text:
        return ""
    # Standard HTML unescape (&nbsp; -> non-breaking space, &amp; -> &, etc.)
    cleaned = html.unescape(text)
    # Convert all Unicode non-breaking and special spaces to standard ASCII space
    cleaned = cleaned.replace('\xa0', ' ').replace('&nbsp;', ' ')
    # Normalize curly quotes and dashes for consistent NLP tokenization
    cleaned = cleaned.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    cleaned = cleaned.replace('—', '-').replace('–', '-')
    return re.sub(r'\s+', ' ', cleaned).strip()


def strip_publisher_watermarks(text: str) -> str:
    """Remove trailing and prominent publisher brand signatures."""
    if not text:
        return ""
    # Strip repeatedly if multiple trailing signatures exist (e.g. '... - PTI - The Hindu')
    prev = None
    curr = text
    while curr != prev:
        prev = curr
        curr = TRAILING_WATERMARK_RE.sub('', curr).strip()
    return curr


def clean_snippet(title: str, snippet: str | None) -> str:
    """Sanitize snippet by removing Google News aggregator list noise and publisher leaks."""
    if not snippet:
        return ""
    
    clean_t = unescape_text(title)
    text = unescape_text(snippet)

    # 1. Google News RSS aggregator detection:
    # If the snippet contains '&nbsp;&nbsp;' or repeats the title followed by source links
    if '&nbsp;&nbsp;' in snippet or ('  ' in snippet and any(p.lower() in snippet.lower() for p in ['scroll', 'bar and bench', 'the hindu', 'ndtv', 'live law', 'etv bharat', 'deccan', 'hindustan times'])):
        # Normalize title and snippet start for comparison
        norm_t = re.sub(r'[^\w\s]', '', clean_t.lower()).strip()
        norm_s = re.sub(r'[^\w\s]', '', text[:len(clean_t) + 30].lower()).strip()
        if norm_t in norm_s or norm_s in norm_t:
            # It's an aggregator list of related links starting with the same title
            return ""

    # 2. If the snippet verbatim repeats the title at the start, strip that repetition
    if clean_t and text.lower().startswith(clean_t.lower()):
        text = text[len(clean_t):].lstrip(' :-–—|.')

    # 3. Strip inline and trailing publisher watermarks
    text = INLINE_WATERMARK_RE.sub(' ', text)
    text = strip_publisher_watermarks(text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 4. If remaining text is too short (< 20 chars) or meaningless noise, discard
    if len(text) < 20 or not any(c.isalpha() for c in text):
        return ""

    return text


def build_clean_evaluation_text(title: str, snippet: str | None = None) -> str:
    """Build the final pure journalistic prose text passed to the neural network.
    
    Guarantees that:
    1. Title is unescaped and stripped of publisher suffixes (e.g. 'Headline - NDTV' -> 'Headline').
    2. Snippet is non-redundant, clean journalistic prose without publisher tags.
    3. The model evaluates only the factual narrative and stylistic choices.
    """
    clean_t = unescape_text(title)
    # Strip any trailing ' - Publisher' from the headline
    clean_t = strip_publisher_watermarks(clean_t)

    clean_s = clean_snippet(clean_t, snippet)

    if clean_s and clean_s.lower() not in clean_t.lower():
        return f"{clean_t}. {clean_s}"
    return clean_t


def clean_text_for_inference(text: str) -> str:
    """Sanitize arbitrary input text passed to predict_text/predict_batch."""
    if not text:
        return ""
    t = unescape_text(text)
    t = INLINE_WATERMARK_RE.sub(' ', t)
    t = strip_publisher_watermarks(t)
    return re.sub(r'\s+', ' ', t).strip()

