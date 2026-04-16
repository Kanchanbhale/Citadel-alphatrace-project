"""
AlphaTrace — Streamlit frontend.
Bloomberg-terminal aesthetic: dark, monospace, teal accents, data-dense.
"""
import json
import os
import time
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AlphaTrace | 13F Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  :root {
    --bg: #0b1020;
    --panel: #111827;
    --panel-2: #0f172a;
    --panel-3: #1f2937;
    --border: #243041;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --muted-2: #64748b;
    --accent: #7c9cff;
    --accent-2: #5b7cff;
    --positive: #22c55e;
    --negative: #ef4444;
    --warning: #f59e0b;
  }

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(180deg, #0a0f1d 0%, #0b1220 100%);
    color: var(--text);
  }

  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px; }

  [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top left, #10192e 0%, #0b1020 42%, #0a0f1d 100%);
  }

  [data-testid="stSidebar"] {
    background: rgba(9, 14, 27, 0.96);
    border-right: 1px solid var(--border);
  }
  [data-testid="stSidebar"] .block-container { padding-top: 1rem; }

  .masthead {
    display:flex; align-items:center; gap:18px;
    padding: 20px 24px;
    background: linear-gradient(135deg, rgba(17,24,39,0.96) 0%, rgba(10,15,29,0.96) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    margin-bottom: 22px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.25);
  }
  .masthead-logo {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #f8fafc;
  }
  .masthead-logo span { color: var(--accent); }
  .masthead-tag {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    border: 1px solid var(--border);
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(148,163,184,0.04);
  }
  .masthead-status {
    margin-left:auto;
    display:flex; align-items:center; gap:8px;
    font-size:11px; font-weight:600; color:#93c5fd;
    letter-spacing:0.08em; text-transform:uppercase;
  }
  .dot {
    width:8px; height:8px; border-radius:50%;
    background: var(--positive);
    box-shadow: 0 0 12px rgba(34,197,94,0.8);
  }

  .section-header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin: 18px 0 14px 0;
  }

  .metric-row { display:flex; gap:14px; margin-bottom:20px; flex-wrap:wrap; }
  .metric-card {
    flex:1; min-width:160px;
    background: linear-gradient(180deg, rgba(17,24,39,0.95) 0%, rgba(15,23,42,0.96) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
  }
  .metric-label {
    font-size: 10px;
    color: var(--muted);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 10px;
  }
  .metric-value { font-size: 20px; font-weight: 700; color: #f8fafc; line-height:1; }
  .metric-sub { font-size: 11px; color: var(--muted-2); margin-top: 8px; }
  .pos { color: var(--positive); }
  .neg { color: var(--negative); }
  .warn { color: var(--warning); }

  .confidence-bar {
    margin-top: 10px;
    height: 6px;
    background: #172132;
    border-radius: 999px;
    overflow: hidden;
  }
  .confidence-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--accent-2), var(--accent));
  }

  .holdings-table {
    width:100%;
    border-collapse:separate;
    border-spacing:0;
    font-size:12px;
    overflow:hidden;
    border:1px solid var(--border);
    border-radius:16px;
    background: rgba(15,23,42,0.9);
  }
  .holdings-table th {
    background:#0f172a;
    color:var(--muted);
    font-size:10px;
    letter-spacing:0.14em;
    text-transform:uppercase;
    padding:12px 14px;
    text-align:left;
    border-bottom:1px solid var(--border);
    font-weight:600;
  }
  .holdings-table td {
    padding:12px 14px;
    border-bottom:1px solid rgba(36,48,65,0.8);
    color:var(--text);
    vertical-align:middle;
  }
  .holdings-table tr:last-child td { border-bottom:none; }
  .holdings-table tr:hover td { background: rgba(124,156,255,0.04); }

  .ticker-badge {
    display:inline-block;
    background: rgba(124,156,255,0.08);
    color: #c7d2fe;
    border: 1px solid rgba(124,156,255,0.28);
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .action-new, .action-added, .action-reduced, .action-exited {
    font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
  }
  .action-new, .action-added { color: var(--positive); }
  .action-reduced, .action-exited { color: var(--negative); }

  .risk-extreme, .risk-high, .risk-medium, .risk-low {
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid transparent;
  }
  .risk-extreme { background: rgba(239,68,68,0.12); color:#fecaca; border-color: rgba(239,68,68,0.3); }
  .risk-high    { background: rgba(245,158,11,0.12); color:#fde68a; border-color: rgba(245,158,11,0.3); }
  .risk-medium  { background: rgba(59,130,246,0.10); color:#bfdbfe; border-color: rgba(59,130,246,0.25); }
  .risk-low     { background: rgba(34,197,94,0.10); color:#bbf7d0; border-color: rgba(34,197,94,0.25); }

  .hypothesis-box {
    background: linear-gradient(180deg, rgba(17,24,39,0.96) 0%, rgba(15,23,42,0.96) 100%);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 22px 24px;
    margin: 10px 0 14px 0;
    font-size: 14px;
    line-height: 1.8;
    color: #e2e8f0;
    box-shadow: 0 10px 30px rgba(0,0,0,0.18);
  }
  .evidence-item {
    display:flex; gap:10px;
    padding:12px 0;
    border-bottom:1px solid rgba(36,48,65,0.8);
    font-size:12px; line-height:1.6;
  }
  .evidence-bullet { color: var(--accent); flex-shrink:0; margin-top:2px; }

  .terminal-box {
    background: rgba(15,23,42,0.95);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.6;
  }

  .stTextInput > div > div > input {
    background: rgba(9,14,27,0.96) !important;
    border: 1px solid var(--border) !important;
    color: #f8fafc !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 16px !important;
    border-radius: 16px !important;
    padding-left: 16px !important;
    min-height: 54px !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px rgba(124,156,255,0.12) !important;
  }

  .stButton > button {
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-2) 100%) !important;
    color: #f8fafc !important;
    border: none !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-radius: 14px !important;
    padding: 0.8rem 1.1rem !important;
    box-shadow: 0 8px 20px rgba(91,124,255,0.28);
  }
  .stButton > button:hover {
    filter: brightness(1.04);
  }

  .stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid var(--border);
    gap: 8px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--muted);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 10px 12px;
    border-bottom: 2px solid transparent;
  }
  .stTabs [aria-selected="true"] {
    color: #f8fafc !important;
    border-bottom: 2px solid var(--accent) !important;
    background: transparent !important;
  }

  [data-testid="stExpander"] {
    background: rgba(15,23,42,0.95);
    border: 1px solid var(--border);
    border-radius: 16px;
  }

  .stDownloadButton > button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--muted) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
  }
  .stDownloadButton > button:hover {
    border-color: var(--accent) !important;
    color: #dbeafe !important;
  }

  .stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--accent-2), var(--accent)) !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_usd(val):
    if not val:
        return "—"
    if val >= 1e9:
        return f"${val/1e9:.2f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


def _action_html(a):
    return f'<span class="action-{a.lower()}">{a}</span>'


def _risk_html(r):
    return f'<span class="risk-{r.lower()}">{r}</span>'


def _signal_html(signal, ret):
    if signal == "POSITIVE" and ret:
        return f'<span class="pos">▲ {ret:.1f}%</span>'
    if signal == "NEGATIVE" and ret:
        return f'<span class="neg">▼ {abs(ret):.1f}%</span>'
    return f'<span style="color:#8b949e">{ret:.1f}%</span>' if ret else '<span style="color:#8b949e">—</span>'


# ── Renderers ─────────────────────────────────────────────────────────────────

def render_masthead():
    st.markdown("""
    <div class="masthead">
      <div class="masthead-logo">Alpha<span>Trace</span></div>
      <div class="masthead-tag">Institutional Holdings Intelligence</div>
      <div class="masthead-status"><span class="dot"></span>Live EDGAR Feed</div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:18px;color:#00d4aa;margin-bottom:4px">AlphaTrace</div>
        <div style="font-size:9px;color:#8b949e;letter-spacing:2px;text-transform:uppercase;margin-bottom:24px">Institutional 13F Research</div>
        <div style="font-size:9px;color:#8b949e;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Quick Queries</div>
        """, unsafe_allow_html=True)

        queries = {
            "🏛 Point72 — Crowding Risk":       "Analyse Point72 latest 13F for crowding risk and new positions",
            "🐯 Tiger Global — New Entries":     "What new positions did Tiger Global open in their latest 13F?",
            "📐 Tiger Global — Alpha Decay":         "Analyse Tiger Global latest 13F for alpha decay signals",
            "🎯 Point72 — Conviction Plays":      "What are Point72 highest-conviction new positions this quarter?",
            "🦅 D.E. Shaw — Portfolio Shifts":    "Analyse D.E. Shaw latest 13F filing for major position changes",
        }
        for label, query in queries.items():
            if st.button(label, key=f"q_{label}", use_container_width=True):
                st.session_state["query_input"] = query
                st.session_state.pop("pipeline_result", None)
                st.session_state.pop("last_query", None)
                st.rerun()

        st.markdown("---")
        st.markdown("""
        <div style="font-size:11px;color:#64748b;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:8px">Data Stack</div>
        <div style="font-size:12px;color:#94a3b8;line-height:2">
          SEC EDGAR / 13F Filings<br>Market Data / yfinance<br>Research Runtime / Live Retrieval
        </div>
        <br>
        <div style="font-size:11px;color:#64748b;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:8px">Pipeline</div>
        <div style="font-size:12px;color:#94a3b8;line-height:2">
          Collector<br>EDA Parallel Fan-out<br>Hypothesis Synthesis
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        st.caption("AlphaTrace Research Console")


def render_metrics(collected, eda, report):
    cur        = collected.get("current_filing", {})
    total_val  = cur.get("total_value_usd", 0)
    total_cnt  = cur.get("total_count", 0)
    deltas     = eda.get("position_deltas", [])
    crowding   = eda.get("crowding_metrics", [])
    if not isinstance(deltas, list): deltas = []
    if not isinstance(crowding, list): crowding = []
    conf       = report.get("confidence_score", 0)
    new_p      = sum(1 for d in deltas if d.get("action") == "NEW")
    exits      = sum(1 for d in deltas if d.get("action") == "EXITED")
    high_risk  = sum(1 for m in crowding if m.get("risk_level") in ("HIGH", "EXTREME"))

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-label">Portfolio AUM</div>
        <div class="metric-value">{_fmt_usd(total_val)}</div>
        <div class="metric-sub">Disclosed 13F value</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Positions</div>
        <div class="metric-value">{total_cnt:,}</div>
        <div class="metric-sub">Total holdings</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">New Entries</div>
        <div class="metric-value pos">{new_p}</div>
        <div class="metric-sub">This quarter</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Full Exits</div>
        <div class="metric-value neg">{exits}</div>
        <div class="metric-sub">Positions unwound</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Crowding Flags</div>
        <div class="metric-value warn">{high_risk}</div>
        <div class="metric-sub">High / extreme risk</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Confidence</div>
        <div class="metric-value">{conf:.0%}</div>
        <div class="confidence-bar"><div class="confidence-fill" style="width:{conf*100:.0f}%"></div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_holdings_tab(collected):
    st.markdown('<div class="section-header">Top Holdings — Current Quarter</div>', unsafe_allow_html=True)
    cur       = collected.get("current_filing", {})
    holdings  = cur.get("holdings", [])
    total_val = cur.get("total_value_usd", 1) or 1

    rows = ""
    for i, h in enumerate(holdings[:20], 1):
        ticker = h.get("ticker") or "—"
        pct    = h.get("value_usd", 0) / total_val * 100
        pc_tag = f' <span style="color:#ff6b35;font-size:9px">{h["put_call"]}</span>' if h.get("put_call") else ""
        rows += f"""
        <tr>
          <td style="color:#8b949e;font-size:10px">{i}</td>
          <td>{h["issuer_name"][:35]}{pc_tag}</td>
          <td><span class="ticker-badge">{ticker}</span></td>
          <td style="text-align:right">{_fmt_usd(h.get("value_usd",0))}</td>
          <td style="text-align:right">{h.get("shares",0):,}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div style="flex:1;height:4px;background:#21262d;border-radius:2px;overflow:hidden">
                <div style="width:{min(100,pct*3):.0f}%;height:100%;background:#00d4aa;border-radius:2px"></div>
              </div>
              <span style="font-size:10px;color:#8b949e;width:36px;text-align:right">{pct:.1f}%</span>
            </div>
          </td>
        </tr>"""

    st.markdown(f"""
    <table class="holdings-table">
      <thead><tr>
        <th>#</th><th>Issuer</th><th>Ticker</th>
        <th style="text-align:right">Mkt Value</th>
        <th style="text-align:right">Shares</th>
        <th>Portfolio %</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)


def render_deltas_tab(eda):
    st.markdown('<div class="section-header">Position Deltas — Quarter-over-Quarter</div>', unsafe_allow_html=True)
    deltas = eda.get("position_deltas", [])
    if not isinstance(deltas, list):
        deltas = []
    deltas = [d for d in deltas if isinstance(d, dict)]
    if not deltas:
        findings = eda.get("key_findings", [])
        msg = findings[0] if findings else "No delta data was generated for this run."
        st.info(msg)
        return
    rows = ""
    for d in deltas[:25]:
        ticker = d.get("ticker") or "—"
        ds     = d.get("delta_shares", 0)
        dp     = d.get("delta_pct", 0)
        sign   = "+" if ds >= 0 else ""
        color  = "#3fb950" if ds >= 0 else "#f85149"
        rows += f"""
        <tr>
          <td>{d["issuer_name"][:35]}</td>
          <td><span class="ticker-badge">{ticker}</span></td>
          <td>{_action_html(d.get("action","—"))}</td>
          <td style="text-align:right">{d.get("prev_shares",0):,}</td>
          <td style="text-align:right">{d.get("curr_shares",0):,}</td>
          <td style="text-align:right;color:{color}">{sign}{ds:,}</td>
          <td style="text-align:right;color:{color}">{sign}{dp:.1f}%</td>
        </tr>"""

    st.markdown(f"""
    <table class="holdings-table">
      <thead><tr>
        <th>Issuer</th><th>Ticker</th><th>Action</th>
        <th style="text-align:right">Prev Shares</th>
        <th style="text-align:right">Curr Shares</th>
        <th style="text-align:right">Δ Shares</th>
        <th style="text-align:right">Δ %</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)


def render_eda_tab(eda):
    corrs = eda.get("price_correlations", [])
    crowding = eda.get("crowding_metrics", [])
    if not isinstance(corrs, list):
        corrs = []
    if not isinstance(crowding, list):
        crowding = []
    corrs = [c for c in corrs if isinstance(c, dict)]
    crowding = [m for m in crowding if isinstance(m, dict)]

    if not corrs and not crowding:
        findings = eda.get("key_findings", [])
        msg = findings[0] if findings else "No EDA outputs were generated for this run."
        st.info(msg)
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Alpha Decay — Return Since Filing</div>', unsafe_allow_html=True)
        rows = ""
        for c in corrs[:15]:
            rows += f"""
            <tr>
              <td><span class="ticker-badge">{c.get("ticker","—")}</span></td>
              <td style="text-align:right">${c.get("price_at_filing") or 0:.2f}</td>
              <td style="text-align:right">${c.get("price_current") or 0:.2f}</td>
              <td style="text-align:right">{_signal_html(c.get("alpha_signal",""), c.get("return_pct"))}</td>
            </tr>"""
        st.markdown(f"""<table class="holdings-table">
          <thead><tr><th>Ticker</th><th style="text-align:right">At Filing</th>
          <th style="text-align:right">Current</th><th style="text-align:right">Return</th></tr></thead>
          <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-header">Smart Money Crowding Risk</div>', unsafe_allow_html=True)
        crowding = eda.get("crowding_metrics", [])
        rows = ""
        for m in crowding[:15]:
            rows += f"""
            <tr>
              <td><span class="ticker-badge">{m.get("ticker","—")}</span></td>
              <td style="text-align:right">{m.get("crowding_score",0):.0f}</td>
              <td>{_risk_html(m.get("risk_level","—"))}</td>
            </tr>"""
        st.markdown(f"""<table class="holdings-table">
          <thead><tr><th>Ticker</th><th style="text-align:right">Score</th><th>Risk Level</th></tr></thead>
          <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)


def render_hypothesis_tab(report):
    if not isinstance(report, dict):
        st.info("Hypothesis report is unavailable for this run.")
        return
    st.markdown('<div class="section-header">Research Hypothesis</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="hypothesis-box">
      <div style="font-size:9px;color:#8b949e;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px">
        {report.get("title","Research Report")}
      </div>
      {report.get("hypothesis","Hypothesis not available.")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Executive Summary</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:12px;line-height:1.8;color:#8b949e;
                border-left:2px solid #21262d;padding-left:12px;margin:8px 0 20px 0">
      {report.get("executive_summary","")}
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Supporting Evidence</div>', unsafe_allow_html=True)
        items = "".join(
            f'<div class="evidence-item"><span class="evidence-bullet">▸</span><span>{e}</span></div>'
            for e in report.get("supporting_evidence", [])
        )
        st.markdown(items, unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="section-header">Risk Factors</div>', unsafe_allow_html=True)
        items = "".join(
            f'<div class="evidence-item"><span style="color:#ff6b35">⚠</span>'
            f'<span style="color:#8b949e">{r}</span></div>'
            for r in report.get("risk_factors", [])
        )
        st.markdown(items, unsafe_allow_html=True)

    warns = report.get("crowding_warnings", [])
    if warns:
        st.markdown('<div class="section-header">Crowding Warnings</div>', unsafe_allow_html=True)
        st.markdown("".join(
            f'<div class="evidence-item"><span style="color:#f85149">■</span>'
            f'<span style="color:#f85149">{w}</span></div>' for w in warns
        ), unsafe_allow_html=True)


def render_charts_tab(eda, report):
    st.markdown('<div class="section-header">Generated Visualisations</div>', unsafe_allow_html=True)
    chart_paths = eda.get("chart_paths", []) if isinstance(eda, dict) else []
    artifact_paths = report.get("artifact_paths", []) if isinstance(report, dict) else []
    if not isinstance(chart_paths, list):
        chart_paths = []
    if not isinstance(artifact_paths, list):
        artifact_paths = []
    all_paths = list(set(chart_paths + artifact_paths))
    pngs = [p for p in all_paths if isinstance(p, str) and p.endswith(".png") and os.path.exists(p)]
    if not pngs:
        findings = eda.get("key_findings", []) if isinstance(eda, dict) else []
        msg = findings[0] if findings else "No chart PNGs were generated. Check visualization generation and outputs/."
        st.info(msg)
        return
    cols = st.columns(2)
    for i, path in enumerate(pngs):
        with cols[i % 2]:
            st.caption(f"📊 {Path(path).stem.replace('_',' ').title()}")
            st.image(path, use_container_width=True)


def render_artifacts_tab(report):
    st.markdown('<div class="section-header">Generated Artifacts</div>', unsafe_allow_html=True)
    paths = report.get("artifact_paths", []) if isinstance(report, dict) else []
    if not isinstance(paths, list):
        paths = []
    if not paths:
        st.info("No artifacts were attached to this run.")
        return
    for path in paths:
        if not os.path.exists(path):
            continue
        fname = Path(path).name
        ext   = Path(path).suffix.lstrip(".")
        icon  = {"png":"🖼","md":"📝","csv":"📊","json":"📋"}.get(ext,"📄")
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #161b22">
              <span>{icon}</span>
              <span style="font-size:12px;color:#c9d1d9">{fname}</span>
              <span style="font-size:10px;color:#8b949e;margin-left:auto">{os.path.getsize(path)/1024:.1f} KB</span>
            </div>""", unsafe_allow_html=True)
        with col2:
            with open(path, "rb") as f:
                st.download_button("↓", data=f, file_name=fname, key=f"dl_{fname}")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    render_masthead()
    render_sidebar()

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        query = st.text_input(
            label="Query",
            placeholder='"Analyse Point72 latest 13F for crowding risk and new positions"',
            key="query_input",
            label_visibility="hidden",
        )
    with col_btn:
        run = st.button("Run →", use_container_width=True)

    if not query:
        st.markdown("""
        <div style="text-align:center;padding:80px 0">
          <div style="font-family:'Syne',sans-serif;font-size:52px;font-weight:800;color:#161b22;margin-bottom:12px">13F</div>
          <div style="font-size:11px;color:#30363d;letter-spacing:3px;text-transform:uppercase">Enter a fund name to begin analysis</div>
        </div>""", unsafe_allow_html=True)
        return

    if run or query:
        cache_key = f"result_{query}"
        if cache_key not in st.session_state:
            from agent_runner import run_pipeline_streaming

            placeholder = st.empty()
            prog        = st.empty()
            step        = 0
            result_json = None

            with st.spinner("Pipeline running…"):
                for msg in run_pipeline_streaming(query):
                    if msg.startswith("{"):
                        result_json = msg
                    else:
                        pct = min(95, int((step + 1) / 7 * 100))
                        placeholder.markdown(f'<div class="terminal-box">▸ {msg}</div>', unsafe_allow_html=True)
                        prog.progress(pct)
                        step += 1

            placeholder.empty()
            prog.empty()

            try:
                st.session_state[cache_key] = json.loads(result_json) if result_json else {"status": "error"}
            except Exception:
                st.session_state[cache_key] = {"status": "error", "raw": result_json}

        result = st.session_state[cache_key]

        if result.get("status") == "error":
            st.error(f"Pipeline error: {result.get('error', result.get('raw', 'Unknown'))}")
            return

        # Extract sub-components (handle flat or nested formats)
        collected = result.get("collected_data") or result
        eda       = result.get("eda_result") or result
        report    = result.get("hypothesis_report") or result
        fund_name = result.get("fund_name") or collected.get("fund_name") or "Fund"
        filing_q  = report.get("filing_quarter", "")

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
          <div style="font-size:24px;font-weight:800;letter-spacing:-0.03em;color:#f8fafc">{fund_name}</div>
          <div style="font-size:11px;color:#94a3b8;letter-spacing:0.12em;text-transform:uppercase;
                      border:1px solid #243041;padding:6px 10px;border-radius:999px;background:rgba(148,163,184,0.04)">{filing_q}</div>
        </div>""", unsafe_allow_html=True)

        render_metrics(collected, eda, report)

        findings = eda.get("key_findings", [])
        if findings:
            ticker_html = "  <span style='color:#21262d;margin:0 10px'>|</span>  ".join(
                f'<span style="color:#c9d1d9">{f[:90]}</span>' for f in findings[:3]
            )
            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.96);border:1px solid #243041;
                        border-radius:16px;padding:14px 18px;margin-bottom:20px;font-size:12px;line-height:1.8">
              <span style="color:#94a3b8;font-size:10px;letter-spacing:0.14em;
                           text-transform:uppercase;margin-right:12px;font-weight:700">Key Findings</span>
              {ticker_html}
            </div>""", unsafe_allow_html=True)

        tabs = st.tabs(["Holdings", "Deltas", "EDA", "Hypothesis", "Charts", "Artifacts"])
        with tabs[0]: render_holdings_tab(collected)
        with tabs[1]: render_deltas_tab(eda)
        with tabs[2]: render_eda_tab(eda)
        with tabs[3]: render_hypothesis_tab(report)
        with tabs[4]: render_charts_tab(eda, report)
        with tabs[5]: render_artifacts_tab(report)

        with st.expander("Raw Pipeline JSON"):
            st.json(result)


if __name__ == "__main__":
    main()
