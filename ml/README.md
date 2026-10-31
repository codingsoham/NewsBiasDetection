# Phase 2: labeling and review

These tools apply the definitions in `guideline.md` verbatim. They use the
stored database from Phase 1; article text remains local except for the text
sent to the configured labeling provider for this research workflow.

Before labeling, create the database with `python ml/collect_indian.py --verify-feeds`,
then `python ml/collect_indian.py`. Use `--backfill` to ingest everything the
feeds currently expose. For a 3,000-record historical target, then run
`python ml/backfill_archives.py --target 3000`; it uses only sitemap locations
declared in publishers' `robots.txt` and is idempotent.

1. Copy `.env.example` to `.env` and set `LLM_API_KEY`, `LLM_API_URL`, and
   `LLM_MODEL`. The endpoint must implement OpenAI-compatible Chat Completions.
2. Run `python ml/llm_label.py --limit 10` first as a paid API sanity check,
   then run `python ml/llm_label.py` to label all articles. Each article gets
   two independent prompt versions. Matching results enter `silver_labels`;
   disagreements are excluded from silver data.
3. Create and host the human review sample:
   `python ml/review.py --prepare 250 --reviewer your_name`.
   Open `http://127.0.0.1:8765`; use L/C/R/N to select a label. Reviews are
   gold labels, saved with reviewer and timestamp.
4. Run `python ml/agreement.py --reviewer your_name` for overall and per-source
   LLM-vs-gold accuracy, Cohen's kappa, and confusion matrices.

The database schema stores LLM prompt version/model/raw response separately
from derived silver labels and human gold labels, so Phase 3 can keep gold data
out of all training splits.
