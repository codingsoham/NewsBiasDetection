"""Mathematically sound Bayesian political prior blending.

Preserves text-model non-political probability, while applying empirical publisher priors
only to the political spectrum (LEFT, CENTER, RIGHT).
"""
from __future__ import annotations
import sys
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

sys.path.append('ml')
sys.path.append('backend')
from training_common import load_split, LABEL_TO_ID, LABELS
from priors import get_outlet_prior


def bayesian_blend(model_probs: dict[str, float], source: str | None, alpha: float = 0.70) -> dict[str, float]:
    p_not_pol = model_probs.get("NOT_POLITICAL", 0.0)
    
    # Text model political mass
    m_left = model_probs.get("LEFT", 0.0)
    m_center = model_probs.get("CENTER", 0.0)
    m_right = model_probs.get("RIGHT", 0.0)
    pol_sum = m_left + m_center + m_right
    if pol_sum <= 1e-6:
        pol_sum = 1.0
        m_center = 1.0

    # Normalized political probabilities from text model
    p_l = m_left / pol_sum
    p_c = m_center / pol_sum
    p_r = m_right / pol_sum

    # Outlet empirical prior [L, C, R]
    prior = get_outlet_prior(source)

    # Blend political stance: text model (alpha) + outlet prior (1 - alpha)
    b_l = alpha * p_l + (1.0 - alpha) * prior[0]
    b_c = alpha * p_c + (1.0 - alpha) * prior[1]
    b_r = alpha * p_r + (1.0 - alpha) * prior[2]
    b_sum = b_l + b_c + b_r

    # Scale by political mass (1 - p_not_pol)
    pol_scale = 1.0 - p_not_pol
    final_l = (b_l / b_sum) * pol_scale
    final_c = (b_c / b_sum) * pol_scale
    final_r = (b_r / b_sum) * pol_scale

    return {
        "LEFT": round(final_l, 4),
        "CENTER": round(final_c, 4),
        "RIGHT": round(final_r, 4),
        "NOT_POLITICAL": round(p_not_pol, 4),
    }


def main():
    te = load_split('data/articles.db', 'test', headline_snippet_only=True)
    raw_probs = np.load('results/curated/test_probabilities.npy')
    gold_ids = [LABEL_TO_ID[r['label']] for r in te]

    for a in [1.0, 0.85, 0.75, 0.65, 0.50]:
        preds = []
        for i, r in enumerate(te):
            t_probs = {LABELS[j]: float(raw_probs[i][j]) for j in range(4)}
            b_probs = bayesian_blend(t_probs, r['source'], alpha=a)
            preds.append(LABEL_TO_ID[max(b_probs, key=b_probs.get)])

        acc = accuracy_score(gold_ids, preds)
        rep = classification_report(gold_ids, preds, target_names=LABELS, output_dict=True, zero_division=0)
        print(f"Alpha={a:.2f} -> Accuracy: {acc:.4f} | Macro-F1: {rep['macro avg']['f1-score']:.4f} | Weighted-F1: {rep['weighted avg']['f1-score']:.4f} | RIGHT-F1: {rep['RIGHT']['f1-score']:.3f} | NOT_POL-F1: {rep['NOT_POLITICAL']['f1-score']:.3f}")


if __name__ == '__main__':
    main()

