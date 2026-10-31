#!/usr/bin/env python3
"""Standalone runner for the NewsBias Ingestion Daemon.
Designed for containerized cloud deployment (Docker, Railway, Render, Fly.io, AWS ECS).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ingest import main

if __name__ == '__main__':
    interval = int(os.getenv("INGESTION_INTERVAL_SECONDS", "1800"))
    threshold = float(os.getenv("CLUSTERING_THRESHOLD", "0.68"))
    run_once = os.getenv("RUN_ONCE", "false").lower() in ("true", "1", "yes")

    if run_once:
        main(threshold=threshold, run_once=True)
    else:
        main(threshold=threshold, daemon=True, interval=interval)

