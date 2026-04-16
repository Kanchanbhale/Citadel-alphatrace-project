"""
Pydantic schemas used throughout the pipeline.
Grab-bag: Structured Output — every stage emits / consumes these models.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Raw holding from a 13F InfoTable ──────────────────────────────────────────
class HoldingRecord(BaseModel):
    issuer_name: str
    cusip: str
    value_usd: float          # in actual dollars (already multiplied by 1000)
    shares: int
    share_type: str = "SH"    # SH or PRN
    put_call: Optional[str] = None
    ticker: Optional[str] = None   # resolved later


# ── Quarter-over-quarter position change ──────────────────────────────────────
class PositionDelta(BaseModel):
    issuer_name: str
    ticker: Optional[str]
    prev_shares: int
    curr_shares: int
    delta_shares: int
    delta_pct: float          # % change
    prev_value_usd: float
    curr_value_usd: float
    action: str               # NEW | ADDED | REDUCED | EXITED | UNCHANGED


# ── Price action since the filing date ────────────────────────────────────────
class PriceCorrelation(BaseModel):
    ticker: str
    issuer_name: str
    price_at_filing: Optional[float]
    price_current: Optional[float]
    return_pct: Optional[float]
    filing_date: str
    alpha_signal: str         # POSITIVE | NEGATIVE | NEUTRAL | UNKNOWN


# ── Fund-overlap / crowding metric for a single ticker ────────────────────────
class CrowdingMetric(BaseModel):
    ticker: str
    issuer_name: str
    num_funds_long: int
    total_shares_held: int
    crowding_score: float     # 0–100
    risk_level: str           # LOW | MEDIUM | HIGH | EXTREME


# ── Aggregated EDA result (all three parallel agents) ─────────────────────────
class EDAResult(BaseModel):
    position_deltas: list[PositionDelta] = Field(default_factory=list)
    price_correlations: list[PriceCorrelation] = Field(default_factory=list)
    crowding_metrics: list[CrowdingMetric] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    chart_paths: list[str] = Field(default_factory=list)


# ── Final research memo / hypothesis ──────────────────────────────────────────
class HypothesisReport(BaseModel):
    title: str
    fund_name: str
    filing_quarter: str
    executive_summary: str
    hypothesis: str
    supporting_evidence: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    top_positions: list[dict] = Field(default_factory=list)
    crowding_warnings: list[str] = Field(default_factory=list)
    confidence_score: float   # 0.0–1.0
    artifact_paths: list[str] = Field(default_factory=list)
    generated_at: str = ""
