# Pre-Phase-6 evidence report

## Protocol and label quality

The database contains 3,000 collected articles. Phase 2 used two independent local-Qwen passes; 2,790 records received an agreed silver label and 210 disagreements were withheld. A 250-item human-review queue was completed. On the 125 reviewed records that also had a silver label, silver versus human agreement is 87.2% (Cohen's kappa 0.828). This is useful silver supervision, not ground truth. The human reviewer saw the suggested label, so anchoring bias remains a documented limitation.

Phase 3 uses 2,649 silver train records, a 125-item human gold validation split, and a disjoint 125-item human gold test split. NDTV and India Today are excluded from training, making test publisher-held-out.

## Gold test results

| System | Accuracy | Macro F1 | Notes |
|---|---:|---:|---|
| Majority baseline | 0.256 | 0.102 | Always CENTER |
| TF-IDF + class-weighted logistic regression | 0.280 | 0.279 | Text-only baseline |
| Public political-bias baseline | 0.160 | 0.069 | Poor cross-domain transfer |
| Direct DistilRoBERTa, weighted loss | **0.416** | **0.445** | Selected local baseline |
| Head-and-tail DistilRoBERTa ablation | 0.392 | 0.419 | Higher validation score (0.527) but worse untouched gold test; rejected |
| Baly Stage 1 only, political subset (n=70) | 0.471 | 0.420 | NOT_POLITICAL excluded because Stage 1 has only three labels |
| Stage 1 then Indian Stage 2 transfer | 0.352 | 0.335 | Worse than direct training; not selected |

The selected model's class F1 values are LEFT 0.444, CENTER 0.407, RIGHT 0.600, and NOT_POLITICAL 0.328. The apparent RIGHT score has high uncertainty because there are only 16 RIGHT items in test and 41 in silver training.

## Calibration, priors, and abstention

Temperature scaling selected T=3.552 on validation. Test ECE falls from 0.499 to 0.221 after scaling. At confidence thresholds 0.25/0.45/0.65, coverage is 100%/84.8%/28.8% and accuracy is 41.6%/39.6%/44.4%, respectively. This supports an `UNCLEAR` state; it does not make the model highly accurate.

On the publisher-held-out test, outlet priors are unavailable for both test publishers and correctly fall back to the global training prior. Model-only scores 0.445 macro F1; prior-only scores 0.140; a 50/50 blend scores 0.354. The deployment therefore uses model-only probabilities rather than smuggling publisher priors into an unseen-publisher evaluation.

## Phase 5 materialization

All 3,000 articles have persisted calibrated predictions. The local materializer uses `all-MiniLM-L6-v2` title+snippet embeddings, a 72-hour window, cross-source rule, cosine threshold, and at least one shared substantive keyword. The recorded sweep at thresholds 0.65/0.70/0.72/0.75/0.80 produced 14/10/9/6/3 stories, with 36/26/23/15/7 linked articles. The database is restored to the documented 0.72 configuration after the sweep.

`backend/test_api.py` passed offline: health, story list/detail, public article lookup, and prediction endpoints all returned HTTP 200. Article body text is never returned by the API.

## Reproduce

Use the project virtual environment and run `python run_all.py` for the offline core evidence. Add `--retrain` to retrain the direct model and `--with-baly` for the expensive Stage-1/Stage-2 experiments. Run `python backend/ingest.py --refresh-rss --refresh-predictions` for a current RSS refresh followed by prediction and story materialization.

## Decision

This is a working, leakage-aware research baseline and a usable local demonstration. It is **not** ready to make reliable real-world claims about political bias: gold data are small, source shift is severe, human review was unblinded, and the selected model's gold macro F1 is 0.445. Phase 6 must preserve the `experimental` and `UNCLEAR` warnings unless a larger blinded gold evaluation improves the evidence.
