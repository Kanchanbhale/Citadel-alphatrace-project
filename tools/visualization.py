"""
Visualization tools.
Grab-bag: Data Visualization — generates and saves charts to disk,
which the Streamlit frontend then displays inline.
"""
from __future__ import annotations
import json
import os
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from config import OUTPUTS_DIR

# ── Design tokens (Bloomberg-dark aesthetic) ──────────────────────────────────
BG       = "#0d1117"
BG2      = "#161b22"
ACCENT   = "#00d4aa"    # teal
WARN     = "#ff6b35"    # orange — risk
POS      = "#3fb950"    # green — positive returns
NEG      = "#f85149"    # red — negative returns
GRID     = "#21262d"
TEXT     = "#c9d1d9"
MUTED    = "#8b949e"

_STYLE: dict[str, Any] = {
    "figure.facecolor":  BG,
    "axes.facecolor":    BG2,
    "axes.edgecolor":    GRID,
    "axes.labelcolor":   TEXT,
    "xtick.color":       MUTED,
    "ytick.color":       MUTED,
    "text.color":        TEXT,
    "grid.color":        GRID,
    "grid.linewidth":    0.5,
    "font.family":       "monospace",
    "axes.spines.top":   False,
    "axes.spines.right": False,
}


def _apply_style():
    plt.rcParams.update(_STYLE)


def _save(fig: plt.Figure, filename: str) -> str:
    path = os.path.join(OUTPUTS_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


# ── Chart generators ──────────────────────────────────────────────────────────

def generate_top_holdings_bar(holdings_json: str, fund_name: str = "Fund") -> str:
    """
    Horizontal bar chart of top 15 holdings by market value.

    Args:
        holdings_json: JSON array of {issuer_name, value_usd, ticker?} dicts.
        fund_name: Label for the chart title.

    Returns:
        Absolute path to saved PNG.
    """
    _apply_style()
    try:
        holdings: list[dict] = json.loads(holdings_json)
    except Exception:
        return json.dumps({"error": "Invalid holdings_json"})

    df = pd.DataFrame(holdings).nlargest(15, "value_usd")
    labels = [
        str(h.get("ticker") or h["issuer_name"][:18]).upper()
        for _, h in df.iterrows()
    ]
    values = df["value_usd"].values / 1e6   # millions

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [ACCENT] * len(values)
    colors[0] = "#f0c040"   # gold for top holding

    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.65)

    ax.set_xlabel("Market Value (USD Millions)", labelpad=8)
    ax.set_title(f"{fund_name} — Top Holdings", fontsize=14, pad=12, color=TEXT, fontweight="bold")
    ax.xaxis.grid(True, alpha=0.4)

    for bar, val in zip(bars, values[::-1]):
        ax.text(
            bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
            f"${val:,.0f}M", va="center", fontsize=7.5, color=MUTED,
        )

    fig.tight_layout()
    return _save(fig, "top_holdings.png")


def generate_position_delta_chart(deltas_json: str, fund_name: str = "Fund") -> str:
    """
    Diverging bar chart: NEW/ADDED positions (green) vs REDUCED/EXITED (red).

    Args:
        deltas_json: JSON array of PositionDelta dicts.
        fund_name: Label for the chart title.

    Returns:
        Absolute path to saved PNG.
    """
    _apply_style()
    try:
        deltas: list[dict] = json.loads(deltas_json)
    except Exception:
        return json.dumps({"error": "Invalid deltas_json"})

    df = pd.DataFrame(deltas)
    if df.empty or "delta_pct" not in df.columns:
        return json.dumps({"error": "No delta data"})

    df = df[df["action"] != "UNCHANGED"].copy()
    df = df.reindex(df["delta_pct"].abs().sort_values(ascending=False).index).head(20)
    labels = [
        str(r.get("ticker") or r["issuer_name"][:16]).upper()
        for _, r in df.iterrows()
    ]

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = [POS if v >= 0 else NEG for v in df["delta_pct"]]
    ax.barh(labels[::-1], df["delta_pct"].values[::-1], color=colors[::-1], height=0.65)
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_xlabel("Quarter-over-Quarter Change (%)", labelpad=8)
    ax.set_title(f"{fund_name} — Position Deltas (QoQ)", fontsize=14, pad=12, fontweight="bold")
    ax.xaxis.grid(True, alpha=0.3)

    add_patch = mpatches.Patch(color=POS, label="Added / New")
    red_patch = mpatches.Patch(color=NEG, label="Reduced / Exited")
    ax.legend(handles=[add_patch, red_patch], loc="lower right", facecolor=BG2, edgecolor=GRID)

    fig.tight_layout()
    return _save(fig, "position_deltas.png")


def generate_crowding_heatmap(crowding_json: str) -> str:
    """
    Colour-coded risk heatmap of crowding scores for top tickers.

    Args:
        crowding_json: JSON array of CrowdingMetric dicts.

    Returns:
        Absolute path to saved PNG.
    """
    _apply_style()
    try:
        metrics: list[dict] = json.loads(crowding_json)
    except Exception:
        return json.dumps({"error": "Invalid crowding_json"})

    df = pd.DataFrame(metrics).sort_values("crowding_score", ascending=False).head(20)
    if df.empty:
        return json.dumps({"error": "No crowding data"})

    labels = [
        str(r.get("ticker") or r["issuer_name"][:14]).upper()
        for _, r in df.iterrows()
    ]
    scores = df["crowding_score"].values

    # Colourmap: green → yellow → red
    cmap = plt.cm.RdYlGn_r
    colours = [cmap(s / 100) for s in scores]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels[::-1], scores[::-1], color=colours[::-1], height=0.65)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Crowding Score (0 = Safe, 100 = Extreme Risk)", labelpad=8)
    ax.set_title("Smart-Money Crowding Risk", fontsize=14, pad=12, fontweight="bold")
    ax.axvline(75, color=WARN, linewidth=1, linestyle="--", alpha=0.7)
    ax.text(75.5, len(labels) - 0.5, "Danger Zone", color=WARN, fontsize=8)
    ax.xaxis.grid(True, alpha=0.3)

    for bar, score in zip(bars, scores[::-1]):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{score:.0f}", va="center", fontsize=8, color=TEXT,
        )

    fig.tight_layout()
    return _save(fig, "crowding_heatmap.png")


def generate_returns_scatter(correlations_json: str) -> str:
    """
    Scatter: return since filing (y) vs. position size rank (x).

    Args:
        correlations_json: JSON array of PriceCorrelation dicts.

    Returns:
        Absolute path to saved PNG.
    """
    _apply_style()
    try:
        corrs: list[dict] = json.loads(correlations_json)
    except Exception:
        return json.dumps({"error": "Invalid correlations_json"})

    df = pd.DataFrame(corrs).dropna(subset=["return_pct"])
    if df.empty:
        return json.dumps({"error": "No correlation data"})

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(df))
    colors = [POS if r >= 0 else NEG for r in df["return_pct"]]

    ax.scatter(x, df["return_pct"], c=colors, s=80, zorder=3, edgecolors=BG2, linewidths=0.5)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.axhline(5, color=POS, linewidth=0.5, linestyle="--", alpha=0.5)
    ax.axhline(-5, color=NEG, linewidth=0.5, linestyle="--", alpha=0.5)

    for i, (_, row) in enumerate(df.iterrows()):
        ax.annotate(
            row.get("ticker", "")[:6],
            (i, row["return_pct"]),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=7,
            color=MUTED,
        )

    ax.set_xlabel("Position Rank (by size)", labelpad=8)
    ax.set_ylabel("Return Since Filing Date (%)", labelpad=8)
    ax.set_title("Alpha Decay Analysis — Return Since 13F Filing", fontsize=14, pad=12, fontweight="bold")
    ax.yaxis.grid(True, alpha=0.3)

    fig.tight_layout()
    return _save(fig, "returns_scatter.png")
