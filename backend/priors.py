"""Publisher bias prior registry for Indian news outlets (Ground News style).

Provides empirical baseline leaning distributions [P(LEFT), P(CENTER), P(RIGHT)]
to anchor short RSS snippets and reflect historical editorial orientation.
"""
from __future__ import annotations
import re

# Empirical Indian Media Leaning Registry: [Left, Center, Right]
# Probabilities sum to 1.0 within the political spectrum.
KNOWN_OUTLET_PRIORS: dict[str, list[float]] = {
    # Established Center-Left / Progressive outlets
    "the wire": [0.65, 0.30, 0.05],
    "wire": [0.65, 0.30, 0.05],
    "scroll": [0.60, 0.35, 0.05],
    "scroll.in": [0.60, 0.35, 0.05],
    "the quint": [0.55, 0.40, 0.05],
    "quint": [0.55, 0.40, 0.05],
    "newslaundry": [0.55, 0.40, 0.05],
    "maktoob": [0.70, 0.25, 0.05],
    "caravan": [0.70, 0.25, 0.05],
    "the caravan": [0.70, 0.25, 0.05],
    "the hindu": [0.42, 0.53, 0.05],
    "hindu": [0.42, 0.53, 0.05],
    "ndtv": [0.38, 0.55, 0.07],
    "deccan herald": [0.35, 0.58, 0.07],
    "telegraph": [0.45, 0.50, 0.05],
    "the telegraph": [0.45, 0.50, 0.05],

    # Established Center / Mainstream Watchdog outlets
    "indian express": [0.18, 0.72, 0.10],
    "the indian express": [0.18, 0.72, 0.10],
    "indian": [0.18, 0.72, 0.10],
    "theprint": [0.18, 0.67, 0.15],
    "print": [0.18, 0.67, 0.15],
    "hindustan times": [0.15, 0.73, 0.12],
    "hindustan": [0.15, 0.73, 0.12],
    "times of india": [0.14, 0.74, 0.12],
    "the times of india": [0.14, 0.74, 0.12],
    "times": [0.14, 0.74, 0.12],
    "free press journal": [0.20, 0.70, 0.10],
    "the statesman": [0.20, 0.70, 0.10],
    "statesman": [0.20, 0.70, 0.10],
    "livemint": [0.08, 0.82, 0.10],
    "mint": [0.08, 0.82, 0.10],
    "economic times": [0.08, 0.82, 0.10],
    "the economic times": [0.08, 0.82, 0.10],
    "press trust of india": [0.05, 0.90, 0.05],
    "pti": [0.05, 0.90, 0.05],
    "ani": [0.08, 0.80, 0.12],
    "ani news": [0.08, 0.80, 0.12],
    "live law": [0.20, 0.75, 0.05],
    "bar and bench": [0.15, 0.80, 0.05],
    "bbc": [0.30, 0.65, 0.05],
    "dw": [0.25, 0.70, 0.05],
    "dw.com": [0.25, 0.70, 0.05],
    "reuters": [0.05, 0.90, 0.05],

    # Established Center-Right / Right-Leaning outlets
    "india today": [0.12, 0.60, 0.28],
    "firstpost": [0.08, 0.48, 0.44],
    "news18": [0.10, 0.58, 0.32],
    "republic": [0.05, 0.30, 0.65],
    "republic world": [0.05, 0.30, 0.65],
    "the pioneer": [0.12, 0.58, 0.30],
    "pioneer": [0.12, 0.58, 0.30],
    "swarajya": [0.04, 0.21, 0.75],
    "opindia": [0.03, 0.17, 0.80],
    "organiser": [0.02, 0.18, 0.80],
    "wion": [0.10, 0.55, 0.35],
}

DEFAULT_BALANCED_PRIOR = [0.18, 0.64, 0.18]


def normalize_source_name(source: str | None) -> str:
    """Normalize messy or truncated RSS source names."""
    if not source:
        return ""
    s = source.strip().lower()
    s = re.sub(r"^(www\.|http://|https://)", "", s)
    s = re.sub(r"\.(com|in|org|net|co\.in)$", "", s)
    s = s.replace("-", " ").replace("_", " ")
    return " ".join(s.split())


def get_outlet_prior(source: str | None) -> list[float]:
    """Retrieve normalized [Left, Center, Right] leaning prior for a publisher."""
    norm = normalize_source_name(source)
    if not norm:
        return list(DEFAULT_BALANCED_PRIOR)

    # 1. Exact match
    if norm in KNOWN_OUTLET_PRIORS:
        return list(KNOWN_OUTLET_PRIORS[norm])

    # 2. Substring match
    for name, prior in KNOWN_OUTLET_PRIORS.items():
        if name in norm or norm in name:
            return list(prior)

    return list(DEFAULT_BALANCED_PRIOR)


def blend_probabilities(
    model_probs: dict[str, float],
    source: str | None,
    alpha: float = 0.65
) -> dict[str, float]:
    """Combine text-model predictions with publisher priors.

    Args:
        model_probs: Model output dict with keys LEFT, CENTER, RIGHT, NOT_POLITICAL.
        source: Publisher/outlet name.
        alpha: Weight given to text model (0.65 model + 0.35 publisher prior).

    Returns:
        Calibrated, blended probabilities dictionary.
    """
    p_not_pol = model_probs.get("NOT_POLITICAL", 0.0)
    # If the text model is overwhelmingly confident the article is non-political,
    # preserve non-political nature.
    if p_not_pol > 0.85:
        return dict(model_probs)

    prior = get_outlet_prior(source)  # [L, C, R]
    m_left = model_probs.get("LEFT", 0.0)
    m_center = model_probs.get("CENTER", 0.0)
    m_right = model_probs.get("RIGHT", 0.0)

    # Normalize political mass
    pol_mass = m_left + m_center + m_right
    if pol_mass <= 0:
        pol_mass = 1.0
        m_left, m_center, m_right = 0.18, 0.64, 0.18

    norm_m_left = m_left / pol_mass
    norm_m_center = m_center / pol_mass
    norm_m_right = m_right / pol_mass

    # Dynamic alpha: when text model has high entropy (uncertain), rely more on publisher prior.
    # When text model is highly polarized/confident, rely more on text model.
    max_prob = max(norm_m_left, norm_m_center, norm_m_right)
    effective_alpha = max(0.50, min(0.85, alpha + (max_prob - 0.40) * 0.3))

    b_left = effective_alpha * norm_m_left + (1.0 - effective_alpha) * prior[0]
    b_center = effective_alpha * norm_m_center + (1.0 - effective_alpha) * prior[1]
    b_right = effective_alpha * norm_m_right + (1.0 - effective_alpha) * prior[2]

    # Preserve non-political mass directly from text model (publisher priors only govern political slant)
    pol_scale = max(0.0, 1.0 - p_not_pol)
    total_b = b_left + b_center + b_right
    if total_b > 0 and pol_scale > 0:
        b_left = (b_left / total_b) * pol_scale
        b_center = (b_center / total_b) * pol_scale
        b_right = (b_right / total_b) * pol_scale
    else:
        b_left, b_center, b_right = 0.0, 0.0, 0.0

    return {
        "LEFT": round(b_left, 4),
        "CENTER": round(b_center, 4),
        "RIGHT": round(b_right, 4),
        "NOT_POLITICAL": round(p_not_pol, 4),
    }

