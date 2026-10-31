"""Shared SQLite, configuration, and label helpers for Phase 2."""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LABELS = ("LEFT", "CENTER", "RIGHT", "NOT_POLITICAL")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dotenv(path: str = ".env") -> None:
    """Load simple KEY=value settings without adding a runtime dependency."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'") )


def db_path(value: str | None = None) -> str:
    return value or os.getenv("ARTICLES_DB", "data/articles.db")


def connect(path: str | None = None) -> sqlite3.Connection:
    target = db_path(path)
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_labeling_schema(connection: sqlite3.Connection) -> None:
    """Create Phase 2 tables; Phase 1 owns the existing articles table."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS llm_annotations (
            id INTEGER PRIMARY KEY,
            article_id INTEGER NOT NULL,
            prompt_version TEXT NOT NULL,
            label TEXT NOT NULL CHECK(label IN ('LEFT','CENTER','RIGHT','NOT_POLITICAL')),
            rationale TEXT NOT NULL,
            confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
            model TEXT NOT NULL,
            raw_response TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(article_id, prompt_version)
        );
        CREATE INDEX IF NOT EXISTS idx_llm_annotations_article ON llm_annotations(article_id);

        CREATE TABLE IF NOT EXISTS silver_labels (
            article_id INTEGER PRIMARY KEY,
            label TEXT NOT NULL CHECK(label IN ('LEFT','CENTER','RIGHT','NOT_POLITICAL')),
            confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
            annotator TEXT NOT NULL DEFAULT 'llm_double_pass',
            prompt_versions TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS review_queue (
            article_id INTEGER PRIMARY KEY,
            suggested_label TEXT NOT NULL CHECK(suggested_label IN ('LEFT','CENTER','RIGHT','NOT_POLITICAL')),
            reason TEXT NOT NULL,
            selected_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS human_reviews (
            id INTEGER PRIMARY KEY,
            article_id INTEGER NOT NULL,
            reviewer_id TEXT NOT NULL,
            label TEXT NOT NULL CHECK(label IN ('LEFT','CENTER','RIGHT','NOT_POLITICAL')),
            reviewed_at TEXT NOT NULL,
            UNIQUE(article_id, reviewer_id)
        );
        CREATE INDEX IF NOT EXISTS idx_human_reviews_article ON human_reviews(article_id);

        CREATE TABLE IF NOT EXISTS dataset_splits (
            article_id INTEGER PRIMARY KEY,
            split TEXT NOT NULL CHECK(split IN ('train','validation','test')),
            label TEXT NOT NULL CHECK(label IN ('LEFT','CENTER','RIGHT','NOT_POLITICAL')),
            provenance TEXT NOT NULL CHECK(provenance IN ('silver','gold')),
            source TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_dataset_splits_split ON dataset_splits(split);
        """
    )
    connection.commit()


def normalise_label(value: object) -> str:
    # Models sometimes echo the guideline's combined display label
    # ("UNCLEAR / NOT_POLITICAL").  Store its canonical database value.
    label = re.sub(r"[^A-Z0-9]+", "_", str(value).upper().strip()).strip("_")
    if label in {"UNCLEAR", "UNCLEAR_NOT_POLITICAL", "NOTPOLITICAL", "NOT_POLITICAL_UNCLEAR"}:
        label = "NOT_POLITICAL"
    if label not in LABELS:
        raise ValueError(f"unsupported label: {value!r}")
    return label
