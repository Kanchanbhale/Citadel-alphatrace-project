"""
Agent runner — uses direct_pipeline for reliable execution.
ADK orchestration is bypassed; tools are called directly in Python.
"""
from __future__ import annotations
import json
import threading
import time
from typing import Any, Generator

from direct_pipeline import run_direct_pipeline


def run_pipeline(query: str) -> dict[str, Any]:
    """Synchronous entry point for Streamlit."""
    return run_direct_pipeline(query)


def run_pipeline_streaming(query: str) -> Generator[str, None, None]:
    """
    Generator that yields status messages while the pipeline runs,
    then yields the final JSON result as the last item.
    """
    result_container: dict[str, Any] = {}
    exception_container: list[Exception] = []

    def _worker():
        try:
            result_container["data"] = run_direct_pipeline(query)
        except Exception as e:
            exception_container.append(e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    status_msgs = [
        "🔍 Resolving fund name → SEC EDGAR CIK lookup...",
        "📥 Fetching current quarter 13F filing (XML parse)...",
        "📥 Fetching prior quarter 13F for delta computation...",
        "💹 Pulling live market prices via yfinance...",
        "⚡ Running parallel EDA — position deltas, alpha decay, crowding...",
        "📊 Generating visualisations (4 charts)...",
        "📝 Synthesising research hypothesis + writing artifacts...",
    ]

    for msg in status_msgs:
        if not t.is_alive():
            break
        yield msg
        time.sleep(4)

    t.join(timeout=240)

    if exception_container:
        err = str(exception_container[0])
        yield f"❌ Error: {err}"
        result_container["data"] = {"status": "error", "error": err}

    result_container.setdefault("data", {"status": "timeout", "error": "Pipeline timed out after 240s"})
    yield json.dumps(result_container["data"])
