"""Explainability and transparency engine for News Bias Detection.

Extracts loaded framing words, distinguishes attribution from editorial stance,
and provides outlet track-record context (Ground News / AllSides style).
"""
from __future__ import annotations
import re

OUTLET_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "the hindu": {
        "editorial": "Center-Left",
        "factuality": "High",
        "description": "National broadsheet with independent editorial stance, traditionally leaning progressive on social and federal policy."
    },
    "the indian express": {
        "editorial": "Center / Watchdog",
        "factuality": "High",
        "description": "Investigative watchdog with a strong tradition of holding incumbent governments accountable across party lines."
    },
    "indian express": {
        "editorial": "Center / Watchdog",
        "factuality": "High",
        "description": "Investigative watchdog with a strong tradition of holding incumbent governments accountable across party lines."
    },
    "theprint": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Digital newsroom featuring balanced viewpoints, mixed opinion contributors, and analytical political commentary."
    },
    "hindustan times": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Major national broadsheet providing mainstream reporting with balanced political analysis."
    },
    "times of india": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Widely circulated commercial broadsheet focusing on mainstream reporting, civic news, and broad reader interest."
    },
    "ndtv": {
        "editorial": "Center-Left",
        "factuality": "High",
        "description": "Major broadcaster and digital publisher known for secular, constitutional, and social welfare focus."
    },
    "livemint": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Financial and policy daily focusing on market reform, fiscal data, and regulatory governance."
    },
    "swarajya": {
        "editorial": "Right",
        "factuality": "Mixed to High",
        "description": "Commentary platform rooted in cultural nationalism, classical liberalism, and economic conservatism."
    },
    "opindia": {
        "editorial": "Right",
        "factuality": "Mixed",
        "description": "Right-wing digital portal focusing on media critique, civilizational narratives, and Hindu cultural advocacy."
    },
    "organiser": {
        "editorial": "Right",
        "factuality": "Mixed",
        "description": "Affiliated with the RSS, championing nationalist policies, cultural heritage, and ideological viewpoints."
    },
    "firstpost": {
        "editorial": "Center-Right",
        "factuality": "High",
        "description": "Digital news network emphasizing strategic geopolitics, robust national security, and governance analysis."
    },
    "india today": {
        "editorial": "Center-Right",
        "factuality": "High",
        "description": "Major national multimedia network with mainstream centrist reporting and patriotic prime-time programming."
    },
    "the wire": {
        "editorial": "Left / Progressive",
        "factuality": "Mixed to High",
        "description": "Non-profit investigative digital publication with an emphasis on civil liberties, minority rights, and state accountability."
    },
    "scroll": {
        "editorial": "Left / Progressive",
        "factuality": "High",
        "description": "Independent digital outlet known for longform cultural reporting, social justice, and opposition viewpoints."
    },
    "the quint": {
        "editorial": "Center-Left",
        "factuality": "High",
        "description": "Mobile-first news outlet focusing on fact-checking, youth politics, and progressive policy."
    },
    "deccan herald": {
        "editorial": "Center-Left",
        "factuality": "High",
        "description": "Prominent South Indian broadsheet with strong federalist, civic, and secular editorial positions."
    },
    "free press journal": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Historic national daily providing direct reporting on politics, civic issues, and regional affairs."
    },
    "bar and bench": {
        "editorial": "Center / Watchdog",
        "factuality": "High",
        "description": "Legal journalism portal covering Supreme Court proceedings, high courts, and constitutional law."
    },
    "live law": {
        "editorial": "Center / Watchdog",
        "factuality": "High",
        "description": "Premier legal reporting network covering judicial benches, legal policy, and constitutional jurisprudence."
    },
    "economic times": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Leading financial daily covering markets, corporate policy, trade, and economic governance."
    },
    "the economic times": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Leading financial daily covering markets, corporate policy, trade, and economic governance."
    },
    "business standard": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Respected financial newspaper focusing on macroeconomic data, corporate affairs, and fiscal policy."
    },
    "business today": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Financial publication focusing on business leadership, macroeconomic trends, and investments."
    },
    "financial express": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Major financial and market daily covering policy, industry, and fiscal developments."
    },
    "moneycontrol": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Leading market and business news portal tracking investments, corporate disclosures, and economic trends."
    },
    "deccan chronicle": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Historic English broadsheet circulating across Telangana and Andhra Pradesh with civic and regional focus."
    },
    "the tribune": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Major North Indian broadsheet published from Chandigarh covering Punjab, Haryana, Himachal, and national news."
    },
    "the statesman": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Historic Kolkata-based daily providing measured commentary on Eastern Indian and national politics."
    },
    "the assam tribune": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Leading English daily of Northeast India, covering regional state politics, security, and border affairs."
    },
    "telegraph india": {
        "editorial": "Center-Left",
        "factuality": "High",
        "description": "Kolkata broadsheet noted for critical front-page headlines and robust government accountability journalism."
    },
    "the telegraph": {
        "editorial": "Center-Left",
        "factuality": "High",
        "description": "Kolkata broadsheet noted for critical front-page headlines and robust government accountability journalism."
    },
    "ani news": {
        "editorial": "Center / Wire",
        "factuality": "High",
        "description": "Major Indian news agency providing syndicated news feeds and direct ground video reporting."
    },
    "ani": {
        "editorial": "Center / Wire",
        "factuality": "High",
        "description": "Major Indian news agency providing syndicated news feeds and direct ground video reporting."
    },
    "reuters": {
        "editorial": "Center / Wire",
        "factuality": "High",
        "description": "Global news organization adhering to strict neutrality and fact-based financial and political reporting."
    },
    "bbc": {
        "editorial": "Center",
        "factuality": "High",
        "description": "International public broadcaster known for investigative reporting, global coverage, and editorial standards."
    },
    "news18": {
        "editorial": "Center-Right",
        "factuality": "High",
        "description": "Prominent multimedia network broadcasting multi-lingual national, regional, and political news."
    },
    "abp live": {
        "editorial": "Center",
        "factuality": "High",
        "description": "Major national broadcasting network providing direct regional and civic news coverage across India."
    },
    "national herald": {
        "editorial": "Left",
        "factuality": "Mixed",
        "description": "Historic publication associated with the Congress movement, offering progressive and opposition commentary."
    },
    "sportskeeda": {
        "editorial": "Non-Political / Sports",
        "factuality": "High",
        "description": "Digital sports publication covering cricket analysis, match statistics, and athlete reporting."
    }
}


def get_source_info(source: str | None, url: str | None = None) -> dict[str, str]:
    """Resolve clean display name, factuality rating, and editorial background for any news source."""
    raw = (source or "").strip()
    clean_lower = raw.lower()
    
    # 1. Normalize truncated names (e.g. 'The' -> 'The Hindu')
    clean_name = raw
    if clean_lower in ("the", "the hindu") or ("thehindu.com" in (url or "").lower()):
        clean_name = "The Hindu"
        clean_lower = "the hindu"
    elif clean_lower in ("times", "times of india") or ("timesofindia" in (url or "").lower()):
        clean_name = "Times of India"
        clean_lower = "times of india"
    elif clean_lower in ("indian", "indian express", "the indian express"):
        clean_name = "The Indian Express"
        clean_lower = "the indian express"
    elif clean_lower in ("theprint", "the print"):
        clean_name = "ThePrint"
        clean_lower = "theprint"
    elif clean_lower in ("scroll", "scroll.in"):
        clean_name = "Scroll.in"
        clean_lower = "scroll"
    elif clean_lower in ("bar and bench", "bar & bench"):
        clean_name = "Bar and Bench"
        clean_lower = "bar and bench"
    elif clean_lower in ("live law", "livelaw"):
        clean_name = "Live Law"
        clean_lower = "live law"
    elif clean_lower in ("wire", "the wire", "thewire.in"):
        clean_name = "The Wire"
        clean_lower = "the wire"
    elif clean_lower in ("hindustan", "hindustan times"):
        clean_name = "Hindustan Times"
        clean_lower = "hindustan times"
    elif clean_lower in ("livemint", "mint"):
        clean_name = "Livemint"
        clean_lower = "livemint"
    elif clean_lower in ("free", "free press journal", "freepress journal"):
        clean_name = "Free Press Journal"
        clean_lower = "free press journal"

    # 2. Match profile from OUTLET_DESCRIPTIONS
    profile = None
    for key, desc in OUTLET_DESCRIPTIONS.items():
        if key == clean_lower or key in clean_lower:
            profile = desc
            if clean_name == raw and len(key) > 4 and clean_name.islower():
                clean_name = key.title()
            break
            
    if not profile:
        profile = {
            "editorial": "General News",
            "factuality": "Standard",
            "description": "Independent commercial news publisher providing regional and national journalistic coverage."
        }
        if not clean_name:
            clean_name = "News Publisher"

    return {
        "name": clean_name,
        "editorial": profile.get("editorial", "Neutral"),
        "factuality": profile.get("factuality", "High"),
        "description": profile.get("description", "Independent commercial news publisher providing regional and national news coverage.")
    }


LOADED_LEXICON: dict[str, str] = {
    # Partisan Conflict / Aggression
    "puppet": "Derogatory characterization",
    "hijacked": "Severe institutional subversion claim",
    "mockery": "Evaluative dismissal of legitimacy",
    "slams": "Conflict framing verb",
    "lashes out": "Emotional confrontation verb",
    "tears into": "Aggressive criticism framing",
    "draconian": "Heavy opposition framing against state actions",
    "witch hunt": "Partisan persecution allegation",
    "vendetta": "Retaliatory political bias allegation",
    "appeasement": "Ideological critique of minority policy",
    "dictatorship": "Severe governance delegitimization",
    "anti-national": "Nationalist critique of dissenters",
    "drags": "Confrontational framing",
    "fumes": "Confrontational framing",
    "cornered": "Adversarial framing",
    "rebel": "Political factionalism marker",
    "crackdown": "Intense enforcement characterization",

    # Triumph / Endorsement
    "masterstroke": "Laudatory editorial framing",
    "historic": "High-impact celebratory framing",
    "unprecedented": "Emphasis framing",
    "visionary": "Laudatory characterization",
    "game changer": "Promotional policy framing",
    "triumphant": "Celebratory outcome marker",
    "decimates": "Adversarial triumph verb",
    "crushes": "Adversarial triumph verb",

    # Suspicion / Devaluation
    "purported": "Distancing / skepticism marker",
    "so-called": "Legitimacy challenge marker",
    "bogus": "Dismissive value judgment",
    "cover-up": "Conspiracy allegation",
    "nexus": "Criminalization of political association",
}

try:
    from backend.attribution_resolver import RIGHT_ACTORS_DICT, LEFT_ACTORS_DICT
except ImportError:
    from attribution_resolver import RIGHT_ACTORS_DICT, LEFT_ACTORS_DICT

INSTITUTIONAL_ACTORS_DICT = {
    r'\bSupreme Court\b': 'Supreme Court',
    r'\bSC\b': 'Supreme Court',
    r'\bCJI\b': 'Chief Justice of India',
    r'\bHigh Court\b': 'High Court',
    r'\bHC\b': 'High Court',
    r'\bCourt\b': 'Court',
    r'\bElection Commission\b': 'Election Commission',
    r'\bEC\b': 'Election Commission',
    r'\bECI\b': 'Election Commission',
    r'\bCEC\b': 'Chief Election Commissioner',
}

ROLE_DISPLAY_NAMES = {
    'MP CM': 'Mohan Yadav (MP CM)',
    'UP CM': 'Yogi Adityanath (UP CM)',
    'Assam CM': 'Himanta Biswa Sarma (Assam CM)',
    'Gujarat CM': 'Bhupendra Patel (Gujarat CM)',
    'Rajasthan CM': 'Bhajan Lal Sharma (Rajasthan CM)',
    'Haryana CM': 'Nayab Singh Saini (Haryana CM)',
    'Odisha CM': 'Mohan Charan Majhi (Odisha CM)',
    'Chhattisgarh CM': 'Vishnu Deo Sai (Chhattisgarh CM)',
    'Uttarakhand CM': 'Pushkar Singh Dhami (Uttarakhand CM)',
    'Goa CM': 'Pramod Sawant (Goa CM)',
    'Karnataka CM': 'Siddaramaiah (Karnataka CM)',
    'Telangana CM': 'Revanth Reddy (Telangana CM)',
    'Himachal CM': 'Sukhvinder Sukhu (Himachal CM)',
    'Tamil Nadu CM': 'M.K. Stalin (TN CM)',
    'TN CM': 'M.K. Stalin (TN CM)',
    'Bengal CM': 'Mamata Banerjee (Bengal CM)',
    'WB CM': 'Mamata Banerjee (Bengal CM)',
    'Kerala CM': 'Pinarayi Vijayan (Kerala CM)',
    'Delhi CM': 'Delhi CM',
    'Punjab CM': 'Bhagwant Mann (Punjab CM)',
    'Jharkhand CM': 'Hemant Soren (Jharkhand CM)',
}


def detect_speaker(title: str, snippet: str = "") -> str | None:
    text = (title or "").strip()
    if not text:
        return None

    # 1. Trailing speaker attribution: e.g. "... : MP CM" or "... - Siddaramaiah"
    trail_match = re.search(r'[:\-–—]\s*([A-Za-z0-9\s.]{2,40})\s*$', text)
    if trail_match:
        candidate = trail_match.group(1).strip()
        # Check against Right actors
        for pat, name in RIGHT_ACTORS_DICT.items():
            if re.fullmatch(pat.strip(r'\b'), candidate, re.IGNORECASE) or re.search(pat, candidate, re.IGNORECASE):
                return ROLE_DISPLAY_NAMES.get(name, name)
        # Check against Left actors
        for pat, name in LEFT_ACTORS_DICT.items():
            if re.fullmatch(pat.strip(r'\b'), candidate, re.IGNORECASE) or re.search(pat, candidate, re.IGNORECASE):
                return ROLE_DISPLAY_NAMES.get(name, name)
        # Check institutional
        for pat, name in INSTITUTIONAL_ACTORS_DICT.items():
            if re.search(pat, candidate, re.IGNORECASE):
                return name

    # 2. Leading SAT (Subject-Action-Target)
    # e.g., 'Want to sow confusion': BJP targets Rahul Gandhi ...
    sat_match = re.search(
        r'(?:^|[\'\"”\s,:;—–-])([A-Za-z0-9\s.]{2,30})\s+(?:slams?|targets?|attacks?|lashes out at|hits? out at|criticizes?|accuses?|alleges?)\b',
        text,
        re.IGNORECASE
    )
    if sat_match:
        cand = sat_match.group(1).strip().strip("'\"“”")
        for pat, name in RIGHT_ACTORS_DICT.items():
            if re.search(pat, cand, re.IGNORECASE):
                return ROLE_DISPLAY_NAMES.get(name, name)
        for pat, name in LEFT_ACTORS_DICT.items():
            if re.search(pat, cand, re.IGNORECASE):
                return ROLE_DISPLAY_NAMES.get(name, name)

    # 3. Attribution verbs: e.g. "<Speaker> says / claims / argues / outlines"
    verb_match = re.search(
        r'(?:^|[\'\"”\s,:;—–-])([A-Za-z0-9\s.]{2,30})\s+(?:says|claims|argues|outlines|warns|denies|alleges|calls for)\b',
        text,
        re.IGNORECASE
    )
    if verb_match:
        cand = verb_match.group(1).strip().strip("'\"“”")
        for pat, name in RIGHT_ACTORS_DICT.items():
            if re.search(pat, cand, re.IGNORECASE):
                return ROLE_DISPLAY_NAMES.get(name, name)
        for pat, name in LEFT_ACTORS_DICT.items():
            if re.search(pat, cand, re.IGNORECASE):
                return ROLE_DISPLAY_NAMES.get(name, name)

    # 4. Institutional fallback in title
    for pat, name in INSTITUTIONAL_ACTORS_DICT.items():
        if re.search(pat, text, re.IGNORECASE):
            return name

    # 5. Entity fallback if not inside quotation marks
    clean_text = re.sub(r"['\"][^'\"]*['\"]", " ", text)
    for pat, name in RIGHT_ACTORS_DICT.items():
        if re.search(pat, clean_text, re.IGNORECASE):
            return ROLE_DISPLAY_NAMES.get(name, name)
    for pat, name in LEFT_ACTORS_DICT.items():
        if re.search(pat, clean_text, re.IGNORECASE):
            return ROLE_DISPLAY_NAMES.get(name, name)

    return None


def extract_explanation(
    title: str | None,
    snippet: str | None,
    source: str | None,
    probs: dict[str, float]
) -> dict:
    """Generate human-readable explainability report for an article."""
    full_text = f"{title or ''} {snippet or ''}".lower()
    
    # 1. Identify loaded framing words present in text
    detected_terms: list[dict[str, str]] = []
    for term, category in LOADED_LEXICON.items():
        # Match as whole word
        if re.search(rf"\b{re.escape(term)}\b", full_text):
            detected_terms.append({"term": term, "meaning": category})

    # 2. Check for quotes or attribution markers and detect speaker accurately
    has_quotes = bool(re.search(r"['\"][^'\"]{4,}['\"]", title or ""))
    has_attribution_verb = bool(re.search(r"\b(says|claims|alleges|accuses|calls|urges|warns|denies|justifies|argues)\b", full_text))
    
    attributed_speaker: str | None = detect_speaker(title or "", snippet or "")
    is_attributed = has_quotes or (has_attribution_verb and attributed_speaker is not None) or (attributed_speaker is not None and bool(re.search(r'[:\-–—]\s*', title or '')))


    # 3. Lookup outlet profile
    clean_src = (source or "").lower().strip()
    profile = None
    for key, desc in OUTLET_DESCRIPTIONS.items():
        if key in clean_src or clean_src in key:
            profile = desc
            profile_outlet = key.title()
            break
    if not profile:
        profile = {
            "editorial": "General News",
            "factuality": "Standard",
            "description": "General reporting publisher."
        }
        profile_outlet = (source or "General News").title()

    # 4. Formulate concise rationale
    highest_label = max(probs, key=probs.get) if probs else "CENTER"
    top_prob = probs.get(highest_label, 0.0) if probs else 0.5
    
    reasons = []
    try:
        from backend.attribution_resolver import resolve_attribution_bias
    except ImportError:
        from attribution_resolver import resolve_attribution_bias
    _, sat_meta = resolve_attribution_bias(title or "", probs)
    if sat_meta:
        reasons.append(f"Attribution stance: {sat_meta['rule']}")

    if detected_terms:
        term_names = [f"'{t['term']}'" for t in detected_terms[:3]]
        reasons.append(f"Framing language detected: {', '.join(term_names)}")

    if is_attributed:
        if attributed_speaker:
            reasons.append(f"Attributed to {attributed_speaker}")
        else:
            reasons.append("Attributed quote in title")

    if profile.get("editorial") and profile["editorial"] not in ("General News", "Center"):
        reasons.append(f"{profile_outlet} editorial track record ({profile['editorial']})")

    if not reasons:
        if highest_label == "NOT_POLITICAL":
            rationale = "Evaluated as civic, technical, or non-partisan reporting."
        elif top_prob > 0.60:
            rationale = f"Factual reporting aligned with {highest_label.title()} policy focus."
        else:
            rationale = "Standard objective reporting without strong partisan markers."
    else:
        rationale = "; ".join(reasons) + "."

    return {
        "loaded_terms": detected_terms[:5],
        "is_attributed": is_attributed,
        "speaker": attributed_speaker,
        "outlet_editorial": profile.get("editorial", "Neutral"),
        "outlet_factuality": profile.get("factuality", "High"),
        "outlet_description": profile.get("description", ""),
        "rationale": rationale
    }

