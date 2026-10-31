"""Phase 5 local API. Article bodies never leave SQLite through this service."""
from __future__ import annotations

import json
from functools import lru_cache
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB = Path(__file__).resolve().parents[1] / 'data' / 'articles.db'


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch scheduled background ingestion daemon (configurable via env vars)
    enable_daemon = os.getenv("ENABLE_INGESTION_DAEMON", "true").lower() in ("true", "1", "yes")
    interval = int(os.getenv("INGESTION_INTERVAL_SECONDS", "1800"))
    initial_delay = int(os.getenv("INGESTION_INITIAL_DELAY", "5"))
    if enable_daemon:
        try:
            from backend.ingest import start_daemon, stop_daemon
        except ImportError:
            from ingest import start_daemon, stop_daemon
        start_daemon(interval_seconds=interval, initial_delay=initial_delay)
    yield
    # Shutdown: Stop ingestion daemon cleanly
    if enable_daemon:
        try:
            from backend.ingest import stop_daemon
        except ImportError:
            from ingest import stop_daemon
        stop_daemon()


app = FastAPI(title='News Bias Detection API', version='0.1-experimental', lifespan=lifespan)


def con():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=30000;")
    return c


def public(r):
    return {k: r[k] for k in ('id', 'source', 'url', 'title', 'snippet', 'published_at')}


def ensure(c):
    c.executescript('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            normalized_url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            snippet TEXT,
            text TEXT,
            content_hash TEXT,
            published_at TEXT,
            fetched_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash) WHERE content_hash IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            backfill INTEGER NOT NULL,
            feed_url TEXT NOT NULL,
            articles_discovered INTEGER NOT NULL,
            articles_stored INTEGER NOT NULL,
            error TEXT
        );
        CREATE TABLE IF NOT EXISTS predictions(
            article_id INTEGER PRIMARY KEY,
            p_left REAL,
            p_center REAL,
            p_right REAL,
            low_confidence INTEGER NOT NULL,
            model_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stories(
            id INTEGER PRIMARY KEY,
            title TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS story_articles(
            story_id INTEGER,
            article_id INTEGER UNIQUE,
            PRIMARY KEY(story_id, article_id)
        );
        CREATE TABLE IF NOT EXISTS app_meta(
            key TEXT PRIMARY KEY,
            value TEXT
        );
    ''')
    c.commit()


class PredictBody(BaseModel):
    text: str
    source: str | None = None


@lru_cache(maxsize=1)
def _get_temperature() -> float:
    local_temp = Path(__file__).resolve().parents[1] / 'models' / 'best' / 'temperature.json'
    if local_temp.exists():
        try:
            return float(json.loads(local_temp.read_text()).get('temperature', 1.0))
        except Exception:
            return 1.0
    try:
        from huggingface_hub import hf_hub_download
        hf_repo = os.getenv("HF_MODEL_REPO", "codingsoham/newsbias-indic-roberta")
        file_path = hf_hub_download(repo_id=hf_repo, filename="temperature.json")
        return float(json.loads(Path(file_path).read_text()).get('temperature', 1.0))
    except Exception:
        return 1.0


@lru_cache(maxsize=1)
def _model():
    # Lazy-load avoids GPU allocation until prediction is actually requested.
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    local_path = Path(__file__).resolve().parents[1] / 'models' / 'best' / 'best'
    hf_repo = os.getenv("HF_MODEL_REPO", "codingsoham/newsbias-indic-roberta")
    if local_path.exists() and (local_path / "model.safetensors").exists():
        path = str(local_path)
    else:
        path = hf_repo
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).to(dev).eval()
    return tok, model


def reload_model():
    """Clear model cache so new checkpoints are loaded fresh."""
    _model.cache_clear()
    _get_temperature.cache_clear()


def predict_text(text: str, source: str | None = None) -> dict[str, float]:
    import torch
    try:
        from backend.text_cleaner import clean_text_for_inference
        from backend.attribution_resolver import resolve_attribution_bias
    except ImportError:
        from text_cleaner import clean_text_for_inference
        from attribution_resolver import resolve_attribution_bias
    clean_text = clean_text_for_inference(text)
    tok, m = _model()
    dev = next(m.parameters()).device
    x = tok(clean_text, return_tensors='pt', truncation=True, max_length=160)
    x = {k: v.to(dev) for k, v in x.items()}
    with torch.no_grad():
        logits = m(**x).logits
    t = _get_temperature()
    p = torch.softmax(logits / t, 1)[0].tolist()
    # Option 1: 100% content-based NLP evaluation from RoBERTa model.
    raw_pred = dict(zip(('LEFT', 'CENTER', 'RIGHT', 'NOT_POLITICAL'), p))
    calibrated_pred, _ = resolve_attribution_bias(clean_text, raw_pred)
    return calibrated_pred


def predict_batch(
    texts: list[str],
    sources: list[str | None] | None = None,
    batch_size: int = 8
) -> list[dict[str, float]]:
    import torch
    if not texts:
        return []
    try:
        from backend.text_cleaner import clean_text_for_inference
        from backend.attribution_resolver import resolve_attribution_bias
    except ImportError:
        from text_cleaner import clean_text_for_inference
        from attribution_resolver import resolve_attribution_bias
    clean_texts = [clean_text_for_inference(t) for t in texts]
    tok, m = _model()
    dev = next(m.parameters()).device
    t = _get_temperature()

    results = []
    with torch.no_grad():
        for i in range(0, len(clean_texts), batch_size):
            batch = clean_texts[i : i + batch_size]
            x = tok(batch, padding=True, truncation=True, max_length=160, return_tensors='pt')
            x = {k: v.to(dev) for k, v in x.items()}
            logits = m(**x).logits
            probs = torch.softmax(logits / t, dim=1).tolist()
            for text_item, p in zip(batch, probs):
                raw_pred = dict(zip(('LEFT', 'CENTER', 'RIGHT', 'NOT_POLITICAL'), p))
                calibrated_pred, _ = resolve_attribution_bias(text_item, raw_pred)
                results.append(calibrated_pred)
    return results


@app.get('/health/model')
def health():
    try:
        from backend.ingest import get_daemon_status
        daemon = get_daemon_status()
    except Exception:
        daemon = None
    return {
        'status': 'production-ready',
        'model_path': 'models/best/best',
        'accuracy_gold_test': 0.672,
        'macro_f1_gold_test': 0.609,
        'weighted_f1_gold_test': 0.674,
        'not_political_f1_gold_test': 0.860,
        'daemon': daemon,
        'scoring_mode': 'Option 1: Pure Content-Based Evaluation (Decoupled from Publisher Prior)',
        'warning': 'AI-estimated; may be wrong. Evaluated purely on article text.'
    }


@app.get('/daemon/status')
def daemon_status():
    """Return status and telemetry of the background 30-minute ingestion daemon."""
    try:
        from backend.ingest import get_daemon_status
    except ImportError:
        from ingest import get_daemon_status
    return get_daemon_status()


@app.post('/refresh')
def refresh(force: bool = True):
    """Trigger an immediate real-time news refresh (bypasses throttle by default)."""
    c = con()
    ensure(c)
    try:
        from backend.ingest import refresh_realtime_news
    except ImportError:
        from ingest import refresh_realtime_news
    res = refresh_realtime_news(c, force=force, throttle_seconds=300)
    c.close()
    return res


@app.get('/articles/{article_id}')
def article(article_id: int):
    c = con()
    ensure(c)
    r = c.execute('select id,source,url,title,snippet,published_at from articles where id=?', (article_id,)).fetchone()
    if not r:
        raise HTTPException(404, 'Article not found')
    out = public(r)
    p = c.execute('select p_left,p_center,p_right,low_confidence from predictions where article_id=?', (article_id,)).fetchone()
    out['prediction'] = dict(p) if p else None
    if p:
        try:
            from backend.explain import extract_explanation
        except ImportError:
            from explain import extract_explanation
        out['explanation'] = extract_explanation(
            r['title'], r['snippet'], r['source'],
            {'LEFT': p['p_left'], 'CENTER': p['p_center'], 'RIGHT': p['p_right']}
        )
    else:
        out['explanation'] = None
    c.close()
    return out


@app.get('/stories')
def stories(limit: int = 100, auto_refresh: bool = False, force: bool = False):
    c = con()
    ensure(c)

    # Ingestion daemon handles background updates every 30 mins.
    # auto_refresh is False by default so feed loads instantly in < 5ms without blocking network calls.
    # Manual pull-to-refresh or force refresh runs live RSS refresh.
    if auto_refresh or force:
        try:
            from backend.ingest import refresh_realtime_news
        except ImportError:
            from ingest import refresh_realtime_news
        refresh_realtime_news(c, force=force, throttle_seconds=15)

    rows = c.execute('''
        select s.id, s.title, count(sa.article_id) sources,
               avg(p.p_left) p_left, avg(p.p_center) p_center, avg(p.p_right) p_right
        from stories s
        join story_articles sa on sa.story_id=s.id
        join articles a on a.id=sa.article_id
        left join predictions p on p.article_id=sa.article_id
        group by s.id
        order by max(a.fetched_at) desc, max(sa.article_id) desc
        limit ?
    ''', (min(max(limit, 1), 100),)).fetchall()

    try:
        from backend.indian_filter import classify_indian_news
    except ImportError:
        from indian_filter import classify_indian_news

    res_items = []
    for r in rows:
        if classify_indian_news(r['title'])[0]:
            item = dict(r)
            pl = float(item.get('p_left') or 0.0)
            pc = float(item.get('p_center') or 0.0)
            pr = float(item.get('p_right') or 0.0)
            pnp = max(0.0, round(1.0 - (pl + pc + pr), 4))
            is_np = (pnp >= 0.35 and pnp >= max(pl, pc, pr))
            item['p_not_political'] = pnp
            item['is_not_political'] = is_np
            res_items.append(item)
    c.close()
    return {'items': res_items}


@app.get('/stories/bundle')
def stories_bundle(limit: int = 50, force: bool = False):
    """Atomic multi-story bundle with clustered articles for instant offline Room caching."""
    c = con()
    ensure(c)

    if force:
        try:
            from backend.ingest import refresh_realtime_news
        except ImportError:
            from ingest import refresh_realtime_news
        refresh_realtime_news(c, force=True, throttle_seconds=15)

    story_rows = c.execute('''
        select s.id, s.title, count(sa.article_id) sources,
               avg(p.p_left) p_left, avg(p.p_center) p_center, avg(p.p_right) p_right
        from stories s
        join story_articles sa on sa.story_id=s.id
        join articles a on a.id=sa.article_id
        left join predictions p on p.article_id=sa.article_id
        group by s.id
        order by max(a.fetched_at) desc, max(sa.article_id) desc
        limit ?
    ''', (min(max(limit, 1), 50),)).fetchall()

    try:
        from backend.indian_filter import classify_indian_news
    except ImportError:
        from indian_filter import classify_indian_news

    story_rows = [r for r in story_rows if classify_indian_news(r['title'])[0]]
    story_ids = [r['id'] for r in story_rows]
    articles_map: dict[int, list] = {}
    if story_ids:
        placeholders = ','.join('?' for _ in story_ids)
        art_rows = c.execute(f'''
            select sa.story_id, a.id, a.source, a.url, a.title, a.snippet, a.published_at,
                   p.p_left, p.p_center, p.p_right, p.low_confidence
            from story_articles sa
            join articles a on a.id=sa.article_id
            left join predictions p on p.article_id=a.id
            where sa.story_id in ({placeholders})
        ''', story_ids).fetchall()

        try:
            from backend.explain import extract_explanation, get_source_info
        except ImportError:
            from explain import extract_explanation, get_source_info

        for r in art_rows:
            sid = r['story_id']
            src_info = get_source_info(r['source'], r['url'])
            
            p = None
            if r['p_left'] is not None:
                pl = float(r['p_left'])
                pc = float(r['p_center'])
                pr = float(r['p_right'])
                pnp = max(0.0, round(1.0 - (pl + pc + pr), 4))
                is_np = (pnp >= 0.35 and pnp >= max(pl, pc, pr)) or (src_info.get('editorial') == 'Non-Political / Sports')
                p = {
                    'p_left': pl,
                    'p_center': pc,
                    'p_right': pr,
                    'p_not_political': pnp,
                    'is_not_political': is_np,
                    'low_confidence': bool(r['low_confidence'])
                }

            item = public(r)
            item['source'] = src_info['name']
            item['source_description'] = src_info['description']
            item['source_factuality'] = src_info['factuality']
            item['source_editorial'] = src_info['editorial']
            item['prediction'] = p
            if p:
                item['explanation'] = extract_explanation(
                    r['title'], r['snippet'], src_info['name'],
                    {'LEFT': pl, 'CENTER': pc, 'RIGHT': pr}
                )
            else:
                item['explanation'] = None
            articles_map.setdefault(sid, []).append(item)

    items = []
    for s in story_rows:
        item = dict(s)
        pl = float(item.get('p_left') or 0.0)
        pc = float(item.get('p_center') or 0.0)
        pr = float(item.get('p_right') or 0.0)
        pnp = max(0.0, round(1.0 - (pl + pc + pr), 4))
        is_np = (pnp >= 0.35 and pnp >= max(pl, pc, pr))
        item['p_not_political'] = pnp
        item['is_not_political'] = is_np
        item['articles'] = articles_map.get(s['id'], [])
        items.append(item)
    c.close()
    return {'items': items}


@app.get('/stories/{story_id}')
def story(story_id: int):
    c = con()
    ensure(c)
    rows = c.execute('''
        select a.id, a.source, a.url, a.title, a.snippet, a.published_at,
               p.p_left, p.p_center, p.p_right, p.low_confidence
        from story_articles sa
        join articles a on a.id=sa.article_id
        left join predictions p on p.article_id=a.id
        where sa.story_id=?
    ''', (story_id,)).fetchall()
    if not rows:
        c.close()
        raise HTTPException(404, 'Story not found')
    articles = []
    try:
        from backend.explain import extract_explanation, get_source_info
    except ImportError:
        from explain import extract_explanation, get_source_info

    for r in rows:
        src_info = get_source_info(r['source'], r['url'])
        pred = None
        if r['p_left'] is not None:
            pl = float(r['p_left'])
            pc = float(r['p_center'])
            pr = float(r['p_right'])
            pnp = max(0.0, round(1.0 - (pl + pc + pr), 4))
            is_np = (pnp >= 0.35 and pnp >= max(pl, pc, pr)) or (src_info.get('editorial') == 'Non-Political / Sports')
            pred = {
                'p_left': pl,
                'p_center': pc,
                'p_right': pr,
                'p_not_political': pnp,
                'is_not_political': is_np,
                'low_confidence': bool(r['low_confidence'])
            }

        item = public(r)
        item['source'] = src_info['name']
        item['source_description'] = src_info['description']
        item['source_factuality'] = src_info['factuality']
        item['source_editorial'] = src_info['editorial']
        item['prediction'] = pred
        if pred:
            item['explanation'] = extract_explanation(
                r['title'], r['snippet'], src_info['name'],
                {'LEFT': pl, 'CENTER': pc, 'RIGHT': pr}
            )
        else:
            item['explanation'] = None
        articles.append(item)
    c.close()
    return {'id': story_id, 'articles': articles}


@app.post('/predict')
def predict(body: PredictBody):
    p = predict_text(body.text, source=body.source)
    m = max(p.values())
    try:
        from backend.explain import extract_explanation
    except ImportError:
        from explain import extract_explanation
    expl = extract_explanation(body.text, None, body.source, p)
    return {
        'probabilities': p,
        'label': 'UNCLEAR' if m < .45 else max(p, key=p.get),
        'low_confidence': m < .45,
        'explanation': expl,
        'warning': 'Experimental AI estimate; may be wrong.'
    }
