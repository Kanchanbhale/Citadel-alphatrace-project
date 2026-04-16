"""
Artifact tools — save persistent outputs to disk.
Grab-bag: Artifacts — research memos, CSVs, and chart PNGs written to ./outputs/.
"""
from __future__ import annotations
import csv
import json
import os
from datetime import datetime

from config import OUTPUTS_DIR


def save_research_memo(content: str, fund_name: str = "fund") -> str:
    """
    Write the final research memo as a markdown file.

    Args:
        content: Full markdown content of the memo.
        fund_name: Used to construct the filename.

    Returns:
        Absolute path to saved .md file.
    """
    safe_name = "".join(c if c.isalnum() else "_" for c in fund_name.lower())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_memo_{safe_name}_{ts}.md"
    path = os.path.join(OUTPUTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_holdings_csv(holdings_json: str, fund_name: str = "fund") -> str:
    """
    Write holdings data as a CSV for downstream analysis.

    Args:
        holdings_json: JSON array of holding dicts.
        fund_name: Used to construct the filename.

    Returns:
        Absolute path to saved .csv file.
    """
    try:
        holdings: list[dict] = json.loads(holdings_json)
    except Exception:
        return json.dumps({"error": "Invalid holdings_json"})

    if not holdings:
        return json.dumps({"error": "No holdings data"})

    safe_name = "".join(c if c.isalnum() else "_" for c in fund_name.lower())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"holdings_{safe_name}_{ts}.csv"
    path = os.path.join(OUTPUTS_DIR, filename)

    fieldnames = list(holdings[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(holdings)

    return path


def save_eda_summary(eda_json: str, fund_name: str = "fund") -> str:
    """
    Persist the full EDA result JSON to disk as an intermediate artifact.

    Args:
        eda_json: JSON string of EDA results.
        fund_name: Used in the filename.

    Returns:
        Absolute path to saved .json file.
    """
    safe_name = "".join(c if c.isalnum() else "_" for c in fund_name.lower())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"eda_summary_{safe_name}_{ts}.json"
    path = os.path.join(OUTPUTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(eda_json)
    return path


def list_artifacts() -> str:
    """List all artifact files in the outputs directory."""
    try:
        files = [
            {
                "name": f,
                "path": os.path.join(OUTPUTS_DIR, f),
                "size_kb": round(os.path.getsize(os.path.join(OUTPUTS_DIR, f)) / 1024, 1),
            }
            for f in os.listdir(OUTPUTS_DIR)
            if not f.startswith(".")
        ]
        files.sort(key=lambda x: x["name"])
        return json.dumps(files)
    except Exception as e:
        return json.dumps({"error": str(e)})
