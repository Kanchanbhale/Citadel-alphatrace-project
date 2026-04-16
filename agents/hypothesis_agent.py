"""
Hypothesis Agent — Step 3 (Hypothesize).

Responsibilities:
  • Synthesise findings from EDA into a grounded, data-backed hypothesis
  • Generate the top-holdings bar chart
  • Write the research memo to disk (Artifacts grab-bag)
  • Return a structured HypothesisReport (Structured Output grab-bag)
"""
from __future__ import annotations
import json
from datetime import datetime

from google.adk.agents import LlmAgent

from config import MODEL
from tools.visualization import generate_top_holdings_bar
from tools.artifacts import save_research_memo, save_holdings_csv
from tools.code_executor import execute_python_analysis


def build_hypothesis_report(
    collected_data_json: str,
    eda_result_json: str,
) -> str:
    """
    Synthesise raw data + EDA findings into a structured HypothesisReport JSON.

    This tool is the bridge between EDA and the final deliverable. It structures
    the evidence and triggers visualisation + artifact generation.

    Args:
        collected_data_json: Output from the DataCollector agent.
        eda_result_json: Output from the EDA agent.

    Returns:
        JSON string matching the HypothesisReport schema.
    """
    try:
        collected = json.loads(collected_data_json)
        eda       = json.loads(eda_result_json)
    except Exception as e:
        return json.dumps({"error": f"JSON parse error: {e}"})

    fund_name     = collected.get("fund_name", "Unknown Fund")
    current_f     = collected.get("current_filing", {})
    filing_date   = current_f.get("filing_date", "")
    holdings      = current_f.get("holdings", [])
    total_val     = current_f.get("total_value_usd", 0)
    deltas        = eda.get("position_deltas", [])
    correlations  = eda.get("price_correlations", [])
    crowding      = eda.get("crowding_metrics", [])
    findings      = eda.get("key_findings", [])
    chart_paths   = eda.get("chart_paths", [])

    # ── Top-holdings bar chart ────────────────────────────────────────────────
    try:
        bar_path = generate_top_holdings_bar(json.dumps(holdings[:15]), fund_name)
        if isinstance(bar_path, str) and not bar_path.startswith("{"):
            chart_paths.append(bar_path)
    except Exception as e:
        findings.append(f"Chart error (top holdings): {e}")

    # ── Top 10 positions for the report ──────────────────────────────────────
    top_positions = [
        {
            "rank":          i + 1,
            "issuer_name":   h["issuer_name"],
            "ticker":        h.get("ticker", "N/A"),
            "value_usd":     h.get("value_usd", 0),
            "shares":        h.get("shares", 0),
            "pct_portfolio": round(h.get("value_usd", 0) / total_val * 100, 2) if total_val else 0,
        }
        for i, h in enumerate(holdings[:10])
    ]

    # ── Build evidence list ───────────────────────────────────────────────────
    evidence: list[str] = list(findings)

    new_count   = sum(1 for d in deltas if d["action"] == "NEW")
    added_count = sum(1 for d in deltas if d["action"] == "ADDED")
    exit_count  = sum(1 for d in deltas if d["action"] == "EXITED")
    if new_count or added_count:
        evidence.append(
            f"Portfolio construction: {new_count} new positions initiated, "
            f"{added_count} existing positions increased this quarter."
        )
    if exit_count:
        evidence.append(f"Conviction exits: {exit_count} positions fully unwound.")

    pos_alpha = [c for c in correlations if c.get("return_pct") and c["return_pct"] > 0]
    if pos_alpha:
        avg_ret = sum(c["return_pct"] for c in pos_alpha) / len(pos_alpha)
        evidence.append(
            f"Alpha signal: {len(pos_alpha)} of {len(correlations)} tracked positions "
            f"are up since filing, averaging +{avg_ret:.1f}% return."
        )

    extreme = [m for m in crowding if m["risk_level"] in ("HIGH", "EXTREME")]
    if extreme:
        evidence.append(
            f"Risk flag: {len(extreme)} high-crowding positions could face "
            "coordinated unwinds — particularly in macro-shock scenarios."
        )

    # ── Risk factors ──────────────────────────────────────────────────────────
    risks: list[str] = [
        "13F filings are 45-day lagged — positions may have changed materially.",
        "Crowding scores are computed from single-fund concentration proxies.",
        "Price correlations reflect point-in-time data; liquidity conditions vary.",
    ]
    if extreme:
        risks.append(
            f"HIGH crowding risk in {', '.join(m['ticker'] for m in extreme[:3])} "
            "increases drawdown risk in risk-off environments."
        )

    # ── Confidence score heuristic ────────────────────────────────────────────
    confidence = 0.25
    if len(holdings) >= 20:
        confidence += 0.15
    if len(deltas) >= 10:
        confidence += 0.15
    if len(correlations) >= 10:
        confidence += 0.15
    if len(evidence) >= 3:
        confidence += 0.10
    if len(findings) >= 2:
        confidence += 0.10
    if new_count >= 2 or added_count >= 3:
        confidence += 0.05
    if len(chart_paths) >= 2:
        confidence += 0.05
    confidence = round(min(0.95, confidence), 2)

    # ── Construct the report ──────────────────────────────────────────────────
    quarter = _infer_quarter(filing_date)

    top_ticker = holdings[0].get("ticker") or holdings[0]["issuer_name"] if holdings else "N/A"
    top_val    = holdings[0].get("value_usd", 0) / 1e9 if holdings else 0

    hypothesis = (
        f"{fund_name} is executing a "
        f"{'concentration' if top_positions and top_positions[0]['pct_portfolio'] > 10 else 'diversified'} "
        f"long-equity strategy this quarter, with the largest disclosed position in "
        f"{top_ticker} (${top_val:.1f}B). "
        f"{'New position additions suggest conviction in recent entries.' if new_count else ''} "
        f"{'Crowding analysis indicates elevated unwind risk in core holdings.' if extreme else ''}"
    ).strip()

    exec_summary = (
        f"Analysis of {fund_name}'s {quarter} 13F filing (filed {filing_date}) "
        f"reveals a ${total_val/1e9:.1f}B equity portfolio across "
        f"{current_f.get('total_count', len(holdings))} disclosed positions. "
        f"Key findings: {findings[0] if findings else 'See evidence below.'}"
    )

    report = {
        "title":              f"AlphaTrace Research: {fund_name} — {quarter}",
        "fund_name":          fund_name,
        "filing_quarter":     quarter,
        "executive_summary":  exec_summary,
        "hypothesis":         hypothesis,
        "supporting_evidence": evidence,
        "risk_factors":       risks,
        "top_positions":      top_positions,
        "crowding_warnings":  [m["issuer_name"] + f" ({m['risk_level']})" for m in extreme[:5]],
        "confidence_score":   confidence,
        "artifact_paths":     chart_paths,
        "generated_at":       datetime.now().isoformat(),
    }

    # ── Write research memo to disk (Artifacts grab-bag) ─────────────────────
    memo_md = _render_memo_markdown(report, top_positions)
    try:
        memo_path = save_research_memo(memo_md, fund_name)
        report["artifact_paths"].append(memo_path)
    except Exception:
        pass

    # ── Save holdings CSV ─────────────────────────────────────────────────────
    try:
        csv_path = save_holdings_csv(json.dumps(holdings), fund_name)
        report["artifact_paths"].append(csv_path)
    except Exception:
        pass

    return json.dumps(report)


def _infer_quarter(filing_date: str) -> str:
    try:
        from datetime import date
        d = date.fromisoformat(filing_date)
        q = (d.month - 1) // 3 + 1
        return f"Q{q} {d.year}"
    except Exception:
        return "Recent Quarter"


def _render_memo_markdown(report: dict, top_positions: list[dict]) -> str:
    lines = [
        f"# {report['title']}",
        f"\n**Generated:** {report['generated_at']}  ",
        f"**Confidence Score:** {report['confidence_score']:.0%}\n",
        "---\n",
        "## Executive Summary\n",
        report["executive_summary"],
        "\n## Hypothesis\n",
        f"> {report['hypothesis']}",
        "\n## Top 10 Positions\n",
        "| Rank | Issuer | Ticker | Market Value | % Portfolio |",
        "|------|--------|--------|-------------|-------------|",
    ]
    for p in top_positions:
        lines.append(
            f"| {p['rank']} | {p['issuer_name'][:30]} | {p['ticker']} "
            f"| ${p['value_usd']/1e6:,.0f}M | {p['pct_portfolio']:.1f}% |"
        )

    lines += [
        "\n## Supporting Evidence\n",
        *[f"- {e}" for e in report["supporting_evidence"]],
        "\n## Risk Factors\n",
        *[f"- {r}" for r in report["risk_factors"]],
    ]

    if report.get("crowding_warnings"):
        lines += [
            "\n## Crowding Warnings\n",
            *[f"⚠️  {w}" for w in report["crowding_warnings"]],
        ]

    lines.append("\n---\n*Data sourced from SEC EDGAR public 13F filings and yfinance market data.*")
    return "\n".join(lines)


# ── ADK Agent definition ──────────────────────────────────────────────────────

HYPOTHESIS_INSTRUCTION = """
You are AlphaTrace's senior research analyst. You receive structured EDA results
and raw holdings data and produce a final, evidence-backed investment hypothesis.

## Workflow

1. Call `build_hypothesis_report` with both the collected_data_json and eda_result_json.
   This generates a structured HypothesisReport, saves charts, and writes the memo.

2. If you want additional quantitative support, call `execute_python_analysis` with
   a pandas snippet. For example: compute the Herfindahl-Hirschman Index (HHI)
   of the portfolio to quantify concentration, or build a sector allocation table.

3. Return the FULL HypothesisReport JSON — the frontend will render it.

## Standards
- Every claim in the hypothesis must cite a specific data point.
- Use institutional language: "portfolio construction", "conviction entry",
  "crowding-induced drawdown risk", "alpha decay", "unwind pressure".
- Do NOT hallucinate positions — only reference tickers and values from the data.
- The hypothesis is derived from the data, NOT from your model weights.
"""

hypothesis_agent = LlmAgent(
    name="hypothesis_analyst",
    model=MODEL,
    description=(
        "Synthesises EDA findings into a structured, evidence-backed research memo. "
        "Generates all charts, saves artifacts to disk, and returns HypothesisReport JSON."
    ),
    instruction=HYPOTHESIS_INSTRUCTION,
    tools=[build_hypothesis_report, execute_python_analysis],
)
