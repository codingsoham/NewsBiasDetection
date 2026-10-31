"""Subject-Action-Target (SAT) & Trailing Speaker Attribution Resolver.
Detects grammatical actor-action-target structures, trailing speaker attributions,
and partisan target-backlash patterns in news headlines to prevent false ideological inversion.
"""
from __future__ import annotations

import re

# Comprehensive mapping of Right-wing / Ruling / NDA actors & roles
RIGHT_ACTORS_DICT = {
    # State CMs & Constitutional Heads
    r'\bMP CM\b': 'MP CM',
    r'\bUP CM\b': 'UP CM',
    r'\bAssam CM\b': 'Assam CM',
    r'\bGujarat CM\b': 'Gujarat CM',
    r'\bRajasthan CM\b': 'Rajasthan CM',
    r'\bHaryana CM\b': 'Haryana CM',
    r'\bOdisha CM\b': 'Odisha CM',
    r'\bChhattisgarh CM\b': 'Chhattisgarh CM',
    r'\bUttarakhand CM\b': 'Uttarakhand CM',
    r'\bGoa CM\b': 'Goa CM',
    r'\bMaharashtra CM\b': 'Maharashtra CM',
    r'\bMaharashtra Dy CM\b': 'Maharashtra Dy CM',
    r'\bMaha Dy CM\b': 'Maharashtra Dy CM',
    r'\bDelhi LG\b': 'Delhi LG',
    r'\bBihar CM\b': 'Bihar CM',
    r'\bAP CM\b': 'AP CM',
    r'\bAndhra CM\b': 'Andhra CM',

    # National & State Leaders
    r'\bBJP\b': 'BJP',
    r'\bBharatiya Janata Party\b': 'BJP',
    r'\bNDA\b': 'NDA',
    r'\bModi\b': 'Modi',
    r'\bPM Modi\b': 'PM Modi',
    r'\bNarendra Modi\b': 'PM Modi',
    r'\bAmit Shah\b': 'Amit Shah',
    r'\bShah\b': 'Amit Shah',
    r'\bYogi\b': 'Yogi Adityanath',
    r'\bYogi Adityanath\b': 'Yogi Adityanath',
    r'\bMohan Yadav\b': 'Mohan Yadav',
    r'\bHimanta\b': 'Himanta Biswa Sarma',
    r'\bHimanta Biswa Sarma\b': 'Himanta Biswa Sarma',
    r'\bRSS\b': 'RSS',
    r'\bVHP\b': 'VHP',
    r'\bCentre\b': 'Centre',
    r'\bCentral Government\b': 'Central Government',
    r'\bUnion Govt\b': 'Union Govt',
    r'\bUnion Government\b': 'Union Government',
    r'\bNirmala Sitharaman\b': 'Nirmala Sitharaman',
    r'\bSitharaman\b': 'Nirmala Sitharaman',
    r'\bKiren Rijiju\b': 'Kiren Rijiju',
    r'\bRijiju\b': 'Kiren Rijiju',
    r'\bJ\.?P\.?\s*Nadda\b': 'J.P. Nadda',
    r'\bNadda\b': 'J.P. Nadda',
    r'\bRajnath Singh\b': 'Rajnath Singh',
    r'\bRajnath\b': 'Rajnath Singh',
    r'\bPiyush Goyal\b': 'Piyush Goyal',
    r'\bSmriti Irani\b': 'Smriti Irani',
    r'\bAnurag Thakur\b': 'Anurag Thakur',
    r'\bSambit Patra\b': 'Sambit Patra',
    r'\bSudhanshu Trivedi\b': 'Sudhanshu Trivedi',
    r'\bShehzad Poonawalla\b': 'Shehzad Poonawalla',
    r'\bPoonawalla\b': 'Shehzad Poonawalla',
    r'\bGaurav Bhatia\b': 'Gaurav Bhatia',
    r'\bDevendra Fadnavis\b': 'Devendra Fadnavis',
    r'\bFadnavis\b': 'Devendra Fadnavis',
    r'\bEknath Shinde\b': 'Eknath Shinde',
}

# Comprehensive mapping of Left-wing / Opposition / INDIA Bloc actors & roles
LEFT_ACTORS_DICT = {
    # State CMs & Constitutional Heads
    r'\bKarnataka CM\b': 'Karnataka CM',
    r'\bKarnataka Dy CM\b': 'Karnataka Dy CM',
    r'\bTelangana CM\b': 'Telangana CM',
    r'\bHimachal CM\b': 'Himachal CM',
    r'\bTamil Nadu CM\b': 'Tamil Nadu CM',
    r'\bTN CM\b': 'Tamil Nadu CM',
    r'\bBengal CM\b': 'Bengal CM',
    r'\bWB CM\b': 'Bengal CM',
    r'\bWest Bengal CM\b': 'Bengal CM',
    r'\bKerala CM\b': 'Kerala CM',
    r'\bDelhi CM\b': 'Delhi CM',
    r'\bPunjab CM\b': 'Punjab CM',
    r'\bJharkhand CM\b': 'Jharkhand CM',

    # National & State Leaders
    r'\bCongress(?:\s+Govt|\s+Government)?\b': 'Congress',
    r'\bINC\b': 'Congress',
    r'\bRahul Gandhi\b': 'Rahul Gandhi',
    r'\bRahul\b': 'Rahul Gandhi',
    r'\bPriyanka Gandhi\b': 'Priyanka Gandhi',
    r'\bPriyanka\b': 'Priyanka Gandhi',
    r'\bSonia Gandhi\b': 'Sonia Gandhi',
    r'\bKharge\b': 'Mallikarjun Kharge',
    r'\bMallikarjun Kharge\b': 'Mallikarjun Kharge',
    r'\bJairam Ramesh\b': 'Jairam Ramesh',
    r'\bPawan Khera\b': 'Pawan Khera',
    r'\bSupriya Shrinate\b': 'Supriya Shrinate',
    r'\bDigvijaya Singh\b': 'Digvijaya Singh',
    r'\bShashi Tharoor\b': 'Shashi Tharoor',
    r'\bTharoor\b': 'Shashi Tharoor',
    r'\bSiddaramaiah\b': 'Siddaramaiah',
    r'\bD\.?K\.?\s*Shivakumar\b': 'D.K. Shivakumar',
    r'\bShivakumar\b': 'D.K. Shivakumar',
    r'\bRevanth Reddy\b': 'Revanth Reddy',
    r'\bRevanth\b': 'Revanth Reddy',
    r'\bINDIA bloc\b': 'INDIA bloc',
    r'\bINDIA Alliance\b': 'INDIA bloc',
    r'\bAAP\b': 'AAP',
    r'\bKejriwal\b': 'Arvind Kejriwal',
    r'\bArvind Kejriwal\b': 'Arvind Kejriwal',
    r'\bAtishi\b': 'Atishi',
    r'\bSanjay Singh\b': 'Sanjay Singh',
    r'\bTMC\b': 'TMC',
    r'\bTrinamool\b': 'TMC',
    r'\bMamata\b': 'Mamata Banerjee',
    r'\bMamata Banerjee\b': 'Mamata Banerjee',
    r'\bAkhilesh\b': 'Akhilesh Yadav',
    r'\bAkhilesh Yadav\b': 'Akhilesh Yadav',
    r'\bSP\b': 'Samajwadi Party',
    r'\bSamajwadi Party\b': 'Samajwadi Party',
    r'\bTejashwi\b': 'Tejashwi Yadav',
    r'\bTejashwi Yadav\b': 'Tejashwi Yadav',
    r'\bRJD\b': 'RJD',
    r'\bDMK\b': 'DMK',
    r'\bM\.?K\.?\s*Stalin\b': 'M.K. Stalin',
    r'\bStalin\b': 'M.K. Stalin',
    r'\bCPI-M\b': 'CPI-M',
    r'\bCPM\b': 'CPI-M',
    r'\bCPI\b': 'CPI',
    r'\bPinarayi Vijayan\b': 'Pinarayi Vijayan',
    r'\bVijayan\b': 'Pinarayi Vijayan',
    r'\bHemant Soren\b': 'Hemant Soren',
    r'\bOpposition\b': 'Opposition',
    r'\bLeft\b': 'Left',
    r'\bUddhav Thackeray\b': 'Uddhav Thackeray',
    r'\bSanjay Raut\b': 'Sanjay Raut',
    r'\bRaut\b': 'Sanjay Raut',
    r'\bSharad Pawar\b': 'Sharad Pawar',
    r'\bMahua Moitra\b': 'Mahua Moitra',
}

ATTACK_VERBS = [
    r'slams?', r'targets?', r'attacks?', r'lashes out at', r'hits? out at', r'tears? into',
    r'corners?', r'criticizes?', r'criticises?', r'fires? at', r'takes? aim at',
    r'demands? resignation of', r'questions?', r'alleges?', r'blames?', r'accuses?'
]

BACKLASH_VERBS = [
    r'faces?\s+(?:fresh\s+|mounting\s+|heavy\s+)?(?:backlash|anger|heat|protests?|flak|criticism|fire)',
    r'(?:under\s+fire|in\s+the\s+dock|in\s+dock|on\s+the\s+backfoot|on\s+backfoot|cornered)'
]

_RIGHT_RE = '|'.join(RIGHT_ACTORS_DICT.keys())
_LEFT_RE = '|'.join(LEFT_ACTORS_DICT.keys())
_VERB_RE = '|'.join(ATTACK_VERBS)
_BACKLASH_RE = '|'.join(BACKLASH_VERBS)

# Pattern 1: Right Actor attacks ... (e.g., 'BJP slams move', 'BJP targets Rahul Gandhi')
RIGHT_ATTACKS_RE = re.compile(
    rf'(?:^|[\'\"”\s,:;—–-])(?:{_RIGHT_RE})\s+(?:{_VERB_RE})\b',
    re.IGNORECASE
)

# Pattern 2: Left Actor attacks ... (e.g., 'Congress slams Modi', 'Rahul Gandhi targets BJP')
LEFT_ATTACKS_RE = re.compile(
    rf'(?:^|[\'\"”\s,:;—–-])(?:{_LEFT_RE})\s+(?:{_VERB_RE})\b',
    re.IGNORECASE
)

# Pattern 3: Left entity faces backlash / anger (e.g., 'Congress Govt faces fresh backlash')
LEFT_FACES_BACKLASH_RE = re.compile(
    rf'(?:{_LEFT_RE})\s+(?:{_BACKLASH_RE})\b',
    re.IGNORECASE
)

# Pattern 4: Right entity faces backlash / anger (e.g., 'BJP faces fresh backlash')
RIGHT_FACES_BACKLASH_RE = re.compile(
    rf'(?:{_RIGHT_RE})\s+(?:{_BACKLASH_RE})\b',
    re.IGNORECASE
)

# Pattern 5: Trailing speaker attribution (e.g. "'Ignorant' Rahul ... : MP CM")
TRAILING_RIGHT_SPEAKER_RE = re.compile(
    rf'[:\-–—]\s*({_RIGHT_RE})\s*$',
    re.IGNORECASE
)

TRAILING_LEFT_SPEAKER_RE = re.compile(
    rf'[:\-–—]\s*({_LEFT_RE})\s*$',
    re.IGNORECASE
)

# Pattern 6: Partisan derogatory attacks against Opposition / Rahul (standard BJP attack tropes)
ANTI_LEFT_SLURS_RE = re.compile(
    r"(?:'Ignorant'\s+Rahul|Rahul\s+spreading\s+anarchy|come\s+from\s+Pak(?:istan)?|Pak\s+agent|\bPappu\b|\bShehzada\b|spreading\s+anarchy)",
    re.IGNORECASE
)

# Pattern 7: Partisan derogatory attacks against Ruling / Modi (standard Opposition attack tropes)
ANTI_RIGHT_SLURS_RE = re.compile(
    r"(?:dictator\s+Modi|fascist\s+BJP|suit\s+boot\s+ki\s+sarkar|crony\s+capitalis[mt])",
    re.IGNORECASE
)


def resolve_attribution_bias(text: str, probs: dict[str, float]) -> tuple[dict[str, float], dict | None]:
    """Calibrate probabilities if the syntactic attacker or trailing speaker contradicts the predicted bias label.
    
    Returns:
        (calibrated_probs, attribution_metadata)
    """
    if not text or not probs:
        return probs, None

    # Strip clean leading clause
    first_clause = text.split(';')[0].split(' - ')[0]

    right_attack = bool(RIGHT_ATTACKS_RE.search(first_clause))
    left_attack = bool(LEFT_ATTACKS_RE.search(first_clause))
    left_backlash = bool(LEFT_FACES_BACKLASH_RE.search(text))
    right_backlash = bool(RIGHT_FACES_BACKLASH_RE.search(text))

    # Trailing speaker detection
    trailing_right = TRAILING_RIGHT_SPEAKER_RE.search(text)
    trailing_left = TRAILING_LEFT_SPEAKER_RE.search(text)

    # Derogatory slur markers
    anti_left_slur = bool(ANTI_LEFT_SLURS_RE.search(text))
    anti_right_slur = bool(ANTI_RIGHT_SLURS_RE.search(text))

    # Case 1: RIGHT STANCE SIGNALS
    # Triggered when:
    # - Right actor attacks target in lead clause (e.g. 'BJP targets Rahul Gandhi')
    # - Left entity faces backlash / anger (e.g. 'Congress Govt faces fresh backlash')
    # - Trailing speaker is a Right actor / CM (e.g. ': MP CM')
    # - Text uses Right-wing derogatory slurs against opposition (e.g. "'Ignorant' Rahul ... come from Pak")
    is_right_signal = (
        (right_attack or left_backlash or trailing_right or (anti_left_slur and trailing_right))
        and not left_attack
        and not trailing_left
    ) or (anti_left_slur and not left_attack)

    if is_right_signal:
        # If model mistakenly gave high LEFT prob because target mentions opposition keywords:
        if probs.get('LEFT', 0.0) > 0.30 or probs.get('LEFT', 0.0) > probs.get('RIGHT', 0.0):
            left_val = probs.get('LEFT', 0.0)
            center_val = probs.get('CENTER', 0.0)
            right_val = probs.get('RIGHT', 0.0)
            np_val = probs.get('NOT_POLITICAL', 0.0)

            # Reallocate the false Left mass into Center (45%) and Right (50%)
            new_probs = {
                'LEFT': round(left_val * 0.05, 4),  # Reduce Left to negligible residual
                'CENTER': round(center_val + (left_val * 0.45), 4),
                'RIGHT': round(right_val + (left_val * 0.50), 4),
                'NOT_POLITICAL': round(np_val, 4)
            }
            total = sum(new_probs.values()) or 1.0
            new_probs = {k: v / total for k, v in new_probs.items()}

            if trailing_right:
                speaker_name = trailing_right.group(1).strip()
                rule_desc = f"Right-wing speaker quote attribution ({speaker_name})"
            elif left_backlash:
                rule_desc = "Left entity facing public backlash/criticism"
            elif anti_left_slur:
                rule_desc = "Partisan criticism directed against Opposition figure"
            else:
                rule_desc = "Right-wing actor attacking target in lead clause"

            meta = {
                'rule': rule_desc,
                'original_top': max(probs, key=probs.get),
                'calibrated_top': max(new_probs, key=new_probs.get)
            }
            return new_probs, meta

    # Case 2: LEFT STANCE SIGNALS
    # Triggered when:
    # - Left/Opposition actor attacks target in lead clause (e.g. 'Congress slams Modi')
    # - Right entity faces backlash (e.g. 'BJP faces protest')
    # - Trailing speaker is a Left actor / CM (e.g. ': Karnataka CM')
    # - Text uses Left-wing derogatory slurs against ruling party (e.g. 'dictator Modi')
    is_left_signal = (
        (left_attack or right_backlash or trailing_left)
        and not right_attack
        and not trailing_right
    ) or (anti_right_slur and not right_attack)

    if is_left_signal:
        if probs.get('RIGHT', 0.0) > 0.30 or probs.get('RIGHT', 0.0) > probs.get('LEFT', 0.0):
            left_val = probs.get('LEFT', 0.0)
            center_val = probs.get('CENTER', 0.0)
            right_val = probs.get('RIGHT', 0.0)
            np_val = probs.get('NOT_POLITICAL', 0.0)

            # Reallocate the false Right mass into Center (45%) and Left (50%)
            new_probs = {
                'LEFT': round(left_val + (right_val * 0.50), 4),
                'CENTER': round(center_val + (right_val * 0.45), 4),
                'RIGHT': round(right_val * 0.05, 4),
                'NOT_POLITICAL': round(np_val, 4)
            }
            total = sum(new_probs.values()) or 1.0
            new_probs = {k: v / total for k, v in new_probs.items()}

            if trailing_left:
                speaker_name = trailing_left.group(1).strip()
                rule_desc = f"Left/Opposition speaker quote attribution ({speaker_name})"
            elif right_backlash:
                rule_desc = "Right entity facing public backlash/criticism"
            elif anti_right_slur:
                rule_desc = "Partisan criticism directed against Ruling party figure"
            else:
                rule_desc = "Left/Opposition actor attacking target in lead clause"

            meta = {
                'rule': rule_desc,
                'original_top': max(probs, key=probs.get),
                'calibrated_top': max(new_probs, key=new_probs.get)
            }
            return new_probs, meta

    return probs, None
