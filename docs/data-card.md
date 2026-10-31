# Data card

## Split policy

- Seed: `20261029`.
- Training contains silver labels only; all 250 human-reviewed gold records are excluded.
- Validation and test contain 125 gold records each.
- Test-only publishers: NDTV, India Today. Their silver records are excluded from training.

## Counts

| Split | Provenance | Total | LEFT | CENTER | RIGHT | NOT_POLITICAL |
|---|---:|---:|---:|---:|---:|---:|
| train | silver | 2649 | 185 | 1666 | 41 | 757 |
| validation | gold | 125 | 23 | 33 | 15 | 54 |
| test | gold | 125 | 22 | 32 | 16 | 55 |

## Publisher coverage

| Publisher | Records across all splits |
|---|---:|
| Indian Express | 2061 |
| The Hindu | 476 |
| Firstpost | 200 |
| Hindustan Times | 100 |
| ThePrint | 20 |
| Times of India | 20 |
| NDTV | 14 |
| India Today | 8 |

## Sources and limitations

- Sources: The Hindu, Indian Express, NDTV, Times of India, Hindustan Times, ThePrint, India Today, and Firstpost.
- The corpus is publisher- and class-imbalanced, especially for RIGHT; use weighted loss and report macro-F1.
- Silver labels come from local Qwen double-pass agreement. Gold labels were manually reviewed, but the review interface displayed suggestions, so gold agreement estimates may be subject to anchoring bias.
- Article text is local research data and must not be served by the API.
