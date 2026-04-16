from __future__ import annotations
import asyncio
import json
from collections import defaultdict

from tools.market_data import compute_price_correlations
from tools.visualization import (
    generate_position_delta_chart,
    generate_crowding_heatmap,
    generate_returns_scatter,
)
from tools.artifacts import save_eda_summary


async def _analyse_position_deltas(current_filing: dict, prior_filing: dict) -> list[dict]:
    current_holdings = current_filing.get("holdings", []) or []
    prior_holdings = prior_filing.get("holdings", []) or []

    def make_key(h: dict):
        return (h.get("cusip") or "", h.get("issuer_name") or "", h.get("ticker") or "")

    cur_map = {make_key(h): h for h in current_holdings}
    prev_map = {make_key(h): h for h in prior_holdings}

    keys = set(cur_map) | set(prev_map)
    deltas: list[dict] = []

    for key in keys:
        cur = cur_map.get(key, {})
        prev = prev_map.get(key, {})

        issuer_name = cur.get("issuer_name") or prev.get("issuer_name") or "Unknown"
        ticker = cur.get("ticker") or prev.get("ticker")
        prev_shares = int(prev.get("shares", 0) or 0)
        curr_shares = int(cur.get("shares", 0) or 0)
        delta_shares = curr_shares - prev_shares

        if prev_shares == 0 and curr_shares > 0:
            action = "NEW"
            delta_pct = 100.0
        elif curr_shares == 0 and prev_shares > 0:
            action = "EXITED"
            delta_pct = -100.0
        elif delta_shares > 0:
            action = "ADDED"
            delta_pct = round((delta_shares / prev_shares) * 100, 2) if prev_shares else 100.0
        elif delta_shares < 0:
            action = "REDUCED"
            delta_pct = round((delta_shares / prev_shares) * 100, 2) if prev_shares else -100.0
        else:
            action = "UNCHANGED"
            delta_pct = 0.0

        deltas.append({
            "issuer_name": issuer_name,
            "ticker": ticker,
            "prev_shares": prev_shares,
            "curr_shares": curr_shares,
            "delta_shares": delta_shares,
            "delta_pct": delta_pct,
            "prev_value_usd": float(prev.get("value_usd", 0) or 0),
            "curr_value_usd": float(cur.get("value_usd", 0) or 0),
            "action": action,
        })

    priority = {"NEW": 0, "ADDED": 1, "REDUCED": 2, "EXITED": 3, "UNCHANGED": 4}
    deltas.sort(key=lambda d: (priority.get(d["action"], 9), -abs(d["delta_shares"])))
    return deltas[:30]


async def _analyse_price_correlations(current_filing: dict) -> list[dict]:
    holdings = current_filing.get("holdings", []) or []
    filing_date = current_filing.get("filing_date", "") or ""
    if not holdings or not filing_date:
        return []

    raw = compute_price_correlations(json.dumps(holdings), filing_date)
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


async def _analyse_crowding(current_filing: dict) -> list[dict]:
    holdings = current_filing.get("holdings", []) or []
    if not holdings:
        return []

    total_value = float(current_filing.get("total_value_usd", 0) or 0)
    metrics: list[dict] = []

    for h in holdings[:25]:
        issuer = h.get("issuer_name", "Unknown")
        ticker = h.get("ticker")
        value_usd = float(h.get("value_usd", 0) or 0)
        shares = int(h.get("shares", 0) or 0)

        weight = (value_usd / total_value * 100) if total_value else 0.0
        crowding_score = min(100.0, round(weight * 5, 2))

        if crowding_score >= 70:
            risk = "EXTREME"
        elif crowding_score >= 40:
            risk = "HIGH"
        elif crowding_score >= 20:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        metrics.append({
            "ticker": ticker,
            "issuer_name": issuer,
            "num_funds_long": 1,
            "total_shares_held": shares,
            "crowding_score": crowding_score,
            "risk_level": risk,
        })

    metrics.sort(key=lambda x: x["crowding_score"], reverse=True)
    return metrics[:20]


def run_parallel_eda_analysis(collected_json: str) -> str:
    try:
        collected = json.loads(collected_json)
    except Exception:
        return json.dumps({"error": "Invalid collected_json"})

    current_filing = collected.get("current_filing", {}) or {}
    prior_filing = collected.get("prior_filing", {}) or {}
    fund_name = collected.get("fund_name", "Fund")

    async def _fan_out():
        return await asyncio.gather(
            _analyse_position_deltas(current_filing, prior_filing),
            _analyse_price_correlations(current_filing),
            _analyse_crowding(current_filing),
        )

    try:
        deltas, correlations, crowding = asyncio.run(_fan_out())
    except Exception as e:
        return json.dumps({"error": f"Parallel execution failed: {e}"})

    findings: list[str] = []
    chart_paths: list[str] = []

    new_count = sum(1 for d in deltas if d.get("action") == "NEW")
    added_count = sum(1 for d in deltas if d.get("action") == "ADDED")
    exited_count = sum(1 for d in deltas if d.get("action") == "EXITED")
    high_risk = [m for m in crowding if m.get("risk_level") in ("HIGH", "EXTREME")]
    positive_corr = [c for c in correlations if c.get("alpha_signal") == "POSITIVE"]

    if new_count:
        findings.append(f"{new_count} new positions identified in the latest quarter.")
    if added_count:
        findings.append(f"{added_count} positions were increased quarter-over-quarter.")
    if exited_count:
        findings.append(f"{exited_count} positions were fully exited.")
    if high_risk:
        findings.append(f"{len(high_risk)} holdings show high or extreme crowding risk.")
    if positive_corr:
        findings.append(f"{len(positive_corr)} holdings show positive return since filing.")

    try:
        p1 = generate_position_delta_chart(json.dumps(deltas), fund_name)
        if isinstance(p1, str) and not p1.startswith("{"):
            chart_paths.append(p1)
    except Exception as e:
        findings.append(f"Chart error (position deltas): {e}")

    try:
        p2 = generate_crowding_heatmap(json.dumps(crowding))
        if isinstance(p2, str) and not p2.startswith("{"):
            chart_paths.append(p2)
    except Exception as e:
        findings.append(f"Chart error (crowding): {e}")

    try:
        p3 = generate_returns_scatter(json.dumps(correlations))
        if isinstance(p3, str) and not p3.startswith("{"):
            chart_paths.append(p3)
    except Exception as e:
        findings.append(f"Chart error (returns): {e}")

    result = {
        "position_deltas": deltas,
        "price_correlations": correlations,
        "crowding_metrics": crowding,
        "key_findings": findings,
        "chart_paths": chart_paths,
    }

    try:
        save_eda_summary(json.dumps(result), fund_name)
    except Exception:
        pass

    return json.dumps(result)
