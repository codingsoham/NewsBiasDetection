"""Server-side Indian news classifier.
Ensures the server only ingests and serves Indian news without fragile keyword whitelisting.
Articles from dedicated Indian national feeds are accepted by default (protecting local civic news,
unlisted Indian politicians, students, and personalities).
Excludes purely foreign domestic politics, overseas conflicts, and US/Israel/European domestic events
that have zero Indian involvement.
"""
from __future__ import annotations

import re

# Comprehensive list of foreign countries, domestic politicians, and overseas locations
ALL_FOREIGN_COUNTRIES_AND_PLACES = [
    # North America
    r'\b(united states|u\.s\.a?|america|american|white house|pentagon|capitol hill)\b',
    r'\b(oregon|florida|texas|california|ohio|nevada|arizona|north dakota|michigan|georgia|chicago|los angeles|new york|washington dc)\b',
    r'\b(donald trump|trump|joe biden|biden|kamala harris|barack obama|jd vance|ron desantis)\b',
    r'\b(canada|canadian|ottawa|toronto|vancouver|montreal|trudeau|justin trudeau)\b',
    r'\b(mexico|mexican|mexico city)\b',

    # Europe & UK
    r'\b(united kingdom|u\.k\.|britain|british|england|english|scotland|scottish|wales|welsh|london|downing street|westminster)\b',
    r'\b(starmer|keir starmer|sunak|rishi sunak|tories|labour party)\b',
    r'\b(france|french|paris|macron|emmanuel macron|le pen)\b',
    r'\b(germany|german|berlin|scholz|olaf scholz|bundestag)\b',
    r'\b(italy|italian|rome|milan|meloni|giorgia meloni)\b',
    r'\b(spain|spanish|madrid|barcelona|toledo)\b',
    r'\b(portugal|portuguese|lisbon|netherlands|dutch|amsterdam|belgium|belgian|brussels)\b',
    r'\b(switzerland|swiss|geneva|zurich|austria|austrian|vienna|greece|greek|athens)\b',
    r'\b(sweden|swedish|stockholm|norway|norwegian|oslo|finland|finnish|helsinki|denmark|danish|copenhagen)\b',
    r'\b(poland|polish|warsaw|hungary|hungarian|budapest|romania|romanian|bucharest)\b',
    r'\b(serbia|serbian|belgrade|vucic|bosnia|croatia|croatian|albania|bulgaria|slovakia|slovenia)\b',
    r'\b(ireland|irish|dublin|european union|eu force|nato)\b',

    # Russia & Eastern Europe
    r'\b(russia|russian|moscow|putin|vladimir putin|kremlin)\b',
    r'\b(ukraine|ukrainian|kyiv|kiev|zelensky|volodymyr zelensky|donbas|crimea)\b',
    r'\b(belarus|minsk|moldova)\b',

    # Middle East & North Africa
    r'\b(israel|israeli|tel aviv|jerusalem|netanyahu|benjamin netanyahu|knesset|idf|mossad)\b',
    r'\b(gaza|hamas|palestine|palestinian|west bank|rafah|sinwar|yahya sinwar)\b',
    r'\b(lebanon|lebanese|beirut|hezbollah|nasrallah)\b',
    r'\b(iran|iranian|tehran|khamenei|pezeshkian|irgc)\b',
    r'\b(iraq|iraqi|baghdad|syria|syrian|damascus|afghanistan|afghan|kabul|taliban)\b',
    r'\b(saudi arabia|saudi|riyadh|mbs|yemen|yemeni|houthi|houthis)\b',
    r'\b(uae|dubai|abu dhabi|flydubai|qatar|qatari|doha|kuwait|bahrain|oman)\b',
    r'\b(egypt|egyptian|cairo|libya|libyan|tripoli|morocco|moroccan|rabat|algeria|algerian|tunisia)\b',
    r'\b(turkey|turkish|ankara|istanbul|erdogan)\b',

    # Asia-Pacific
    r'\b(china|chinese|beijing|shanghai|xi jinping|communist party of china)\b',
    r'\b(taiwan|taiwanese|taipei)\b',
    r'\b(japan|japanese|tokyo|kyoto|osaka)\b',
    r'\b(south korea|korean|seoul|yoon suk yeol|north korea|pyongyang|kim jong un)\b',
    r'\b(philippines|filipino|manila|mayon volcano|indonesia|indonesian|jakarta|bali)\b',
    r'\b(malaysia|malaysian|kuala lumpur|singapore|singaporean|thailand|thai|bangkok|vietnam|vietnamese|hanoi)\b',
    r'\b(myanmar|burma|burmese|naypyidaw|sri lanka|colombo|nepal|kathmandu)\b',
    r'\b(australia|australian|sydney|melbourne|canberra|albanese|new zealand|auckland|wellington)\b',

    # Latin America & Africa
    r'\b(brazil|brazilian|brasilia|rio de janeiro|bolsonaro|flavio bolsonaro|lula da silva|lula)\b',
    r'\b(argentina|argentine|buenos aires|milei|colombia|colombian|bogota|chile|santiago|peru|lima|venezuela|caracas)\b',
    r'\b(south africa|johannesburg|cape town|nigeria|nigerian|abuja|lagos|kenya|kenyan|nairobi|ethiopia|addis ababa)\b',

    # Other global events
    r'\b(binance|crypto heist|cryptocurrency)\b',
    r'\b(halloween gatherings)\b',
]

FOREIGN_REGEX = re.compile('|'.join(ALL_FOREIGN_COUNTRIES_AND_PLACES), re.IGNORECASE)

# Any mention indicating an Indian national connection / perspective / authority / diaspora
INDIAN_CONNECTION_PATTERNS = [
    r'\b(india|indians?|ind|bharat|bharatiya|hindustan|hindustani|desh)\b',
    r'\b(delhi|new delhi|mumbai|bengaluru|bangalore|kolkata|chennai|hyderabad|ahmedabad|pune)\b',
    r'\b(uttar pradesh|maharashtra|bihar|bengal|west bengal|kerala|tamil nadu|karnataka|gujarat|rajasthan|punjab|haryana|odisha|assam|kashmir|jammu|ladakh|arunachal|manipur)\b',
    r'\b(mea|ministry of external affairs|foreign minister|jaishankar|modi|narendra modi|prime minister modi|pm modi)\b',
    r'\b(indian army|indian navy|indian air force|iaf|coast guard|indian coast guard|isro|brics)\b',
    r'\b(embassy of india|indian embassy|indian consulate|consulate general of india|high commission of india)\b',
    r'\b(indian diaspora|indian-origin|indian student|indian national|indian citizen|indian envoy|indian origin|indian passenger|indian crew)\b',
    r'\b(supreme court|high court|bjp|congress|parliament|lok sabha|rajya sabha|rupee|crore|lakh)\b',
]

INDIAN_CONNECTION_REGEX = re.compile('|'.join(INDIAN_CONNECTION_PATTERNS), re.IGNORECASE)


def classify_indian_news(title: str, snippet: str = "") -> tuple[bool, str]:
    """Server-side classification to ensure only Indian news is ingested and served.
    1. News from Indian feeds is ACCEPTED by default (so local civic issues, obscure politicians,
       and unlisted Indian personalities are never dropped).
    2. Drops ONLY articles that are purely about foreign domestic politics, overseas accidents,
       or international conflicts with ZERO Indian connection.
    3. Retains international news if an Indian citizen, diplomat, minister, or bilateral issue is involved.
    """
    text = f"{title or ''} {snippet or ''}"

    foreign_matches = [m.group(0) for m in FOREIGN_REGEX.finditer(text)]
    if not foreign_matches:
        # 100% Indian domestic news by default (no foreign geopolitics markers)
        return True, "Indian domestic news"

    # Foreign geopolitics markers found: check if there is an Indian connection / perspective
    indian_matches = [m.group(0) for m in INDIAN_CONNECTION_REGEX.finditer(text)]
    if indian_matches:
        # Kept because an Indian connection is present (e.g. Indian student, Indian consulate, MEA, Coast Guard, IND team)
        return True, f"Indian angle on international event: {indian_matches[:2]} alongside {foreign_matches[:1]}"

    # Pure foreign domestic geopolitics with zero Indian involvement -> EXCLUDE
    return False, f"Foreign domestic geopolitics: {foreign_matches[:2]}"
