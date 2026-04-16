"""
Direct pipeline — bypasses ADK agent orchestration entirely.
Calls tools directly in Python for reliable structured output.
"""
from __future__ import annotations
import json
import re
from config import KNOWN_FUND_CIKS
from tools.sec_edgar import search_fund_cik, get_fund_filings, fetch_13f_holdings
from tools.market_data import get_current_prices, get_sector_breakdown
from agents.eda_agent import run_parallel_eda_analysis
from agents.hypothesis_agent import build_hypothesis_report

# ── Fund name aliases ─────────────────────────────────────────────────────────
FUND_ALIASES: dict[str, str] = {
    "citadel":       "Citadel Advisors",
    "tiger global":  "Tiger Global",
    "two sigma":     "Two Sigma",
    "point72":       "Point72",
    "d.e. shaw":     "D.E. Shaw",
    "de shaw":       "D.E. Shaw",
    "shaw":          "D.E. Shaw",
    "millennium":    "Millennium Management",
    "renaissance":   "Renaissance Technologies",
    "ren tech":      "Renaissance Technologies",
    "bridgewater":   "Bridgewater Associates",
    "viking":        "Viking Global",
    "coatue":        "Coatue Management",
    "baupost":       "Baupost Group",
    "pershing":      "Pershing Square",
    "ackman":        "Pershing Square",
    "third point":   "Third Point",
    "loeb":          "Third Point",
    "appaloosa":     "Appaloosa Management",
    "druckenmiller": "Duquesne Family Office",
    "duquesne":      "Duquesne Family Office",
    "whale rock":    "Whale Rock Capital",
}


def extract_fund_name(query: str) -> str:
    """Pull the most likely fund name from a free-text query."""
    q = query.lower()
    for key, canonical in FUND_ALIASES.items():
        if key in q:
            return canonical
    # Check KNOWN_FUND_CIKS keys
    for key in KNOWN_FUND_CIKS:
        if key in q:
            return key.title()
    # Last resort: grab first title-cased word longer than 3 chars
    for word in query.split():
        if len(word) > 3 and word[0].isupper():
            return word
    return query[:40]


def run_direct_pipeline(query: str) -> dict:
    """
    Execute the full Collect → EDA → Hypothesize pipeline directly.
    Returns a dict compatible with app.py's rendering expectations.
    """
    fund_name = extract_fund_name(query)

    # ── Step 1: Collect ───────────────────────────────────────────────────────
    try:
        cik_data = json.loads(search_fund_cik(fund_name))
    except Exception as e:
        return {"status": "error", "error": f"EDGAR search failed: {e}"}

    if not cik_data.get("cik"):
        return {"status": "error", "error": f"Fund '{fund_name}' not found on SEC EDGAR. Try a more specific name."}

    cik             = cik_data["cik"]
    actual_name     = cik_data.get("name", fund_name)

    try:
        filings_data = json.loads(get_fund_filings(cik))
    except Exception as e:
        return {"status": "error", "error": f"Could not fetch filings: {e}"}

    filings = filings_data.get("filings", [])
    if not filings:
        return {"status": "error", "error": f"No 13F filings found for {actual_name} (CIK {cik})."}

    # Fetch current quarter
    try:
        current_data = json.loads(fetch_13f_holdings(cik, filings[0]["accession_number"]))
        current_data["filing_date"] = filings[0].get("filing_date", "")
        current_data["total_count"] = current_data.get("total_count", len(current_data.get("holdings", [])))
    except Exception as e:
        return {"status": "error", "error": f"Could not parse 13F XML: {e}"}

    # Fetch prior quarter (for deltas)
    prior_data: dict = {}
    if len(filings) > 1:
        try:
            prior_data = json.loads(fetch_13f_holdings(cik, filings[1]["accession_number"]))
            prior_data["filing_date"] = filings[1].get("filing_date", "")
        except Exception:
            prior_data = {}

    # Live market prices
    holdings    = current_data.get("holdings", [])
    tickers     = [h["ticker"] for h in holdings if h.get("ticker")][:20]
    prices: dict = {}
    if tickers:
        try:
            prices = json.loads(get_current_prices(json.dumps(tickers)))
        except Exception:
            prices = {}

    collected = {
        "fund_name":      actual_name,
        "cik":            cik,
        "current_filing": current_data,
        "prior_filing":   prior_data,
        "current_prices": prices,
        "sector_map":     {},
    }

    # ── Step 2: EDA (parallel fan-out) ───────────────────────────────────────
    try:
        eda_data = json.loads(run_parallel_eda_analysis(json.dumps(collected)))
        if not isinstance(eda_data, dict):
            eda_data = {}
        if eda_data.get("error"):
            eda_data = {
                "position_deltas":    [],
                "price_correlations": [],
                "crowding_metrics":   [],
                "key_findings":       [f"EDA error: {eda_data.get('error')}"],
                "chart_paths":        [],
            }
    except Exception as e:
        eda_data = {
            "position_deltas":    [],
            "price_correlations": [],
            "crowding_metrics":   [],
            "key_findings":       [f"EDA error: {e}"],
            "chart_paths":        [],
        }

    # ── Step 3: Hypothesize ───────────────────────────────────────────────────
    try:
        report_data = json.loads(
            build_hypothesis_report(json.dumps(collected), json.dumps(eda_data))
        )
    except Exception as e:
        report_data = {
            "title":              f"AlphaTrace: {actual_name}",
            "fund_name":          actual_name,
            "filing_quarter":     current_data.get("filing_date", "")[:7],
            "executive_summary":  "Report generation encountered an error.",
            "hypothesis":         f"Hypothesis unavailable: {e}",
            "supporting_evidence": [],
            "risk_factors":       [],
            "top_positions":      [],
            "crowding_warnings":  [],
            "confidence_score":   0.5,
            "artifact_paths":     [],
            "generated_at":       "",
        }

    return {
        "status":           "complete",
        "fund_name":        actual_name,
        "pipeline_steps":   ["collect", "eda", "hypothesize"],
        "collected_data":   collected,
        "eda_result":       eda_data,
        "hypothesis_report": report_data,
    }
