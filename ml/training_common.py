"""Shared Phase 4 data, device, and text helpers."""
from __future__ import annotations
import sqlite3
from pathlib import Path

LABELS = ('LEFT', 'CENTER', 'RIGHT', 'NOT_POLITICAL')
LABEL_TO_ID = {x: i for i, x in enumerate(LABELS)}


def load_split(db_path: str, split: str, head_tail: bool = False, headline_snippet_only: bool = True):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """SELECT a.id, a.title, a.snippet, a.text, d.label, d.source
           FROM dataset_splits d JOIN articles a ON a.id=d.article_id
           WHERE d.split=?""",
        (split,)
    ).fetchall()
    return [
        dict(r, text=article_text(r['title'], r['snippet'], r['text'], head_tail, headline_snippet_only))
        for r in rows
    ]


def article_text(title: str | None, snippet: str | None, body: str | None = None, head_tail: bool = False, headline_snippet_only: bool = True) -> str:
    """Format article text for model input.

    If headline_snippet_only is True, uses title + snippet directly,
    ensuring 100% feature parity between training and real-time RSS inference.
    """
    if headline_snippet_only or not body:
        parts = [p.strip() for p in (title or '', snippet or '') if p and p.strip()]
        return ' '.join(parts)

    text = ' '.join(x for x in (title, snippet, body) if x).strip()
    return (text[:1400] + ' [SEP] ' + text[-1400:]) if head_tail and len(text) > 2800 else text[:2800]


def device_summary():
    import torch
    return {
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'cuda': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'vram_gb': round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1) if torch.cuda.is_available() else 0
    }
