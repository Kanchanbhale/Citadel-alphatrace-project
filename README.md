# AlphaTrace — Institutional 13F Intelligence Platform

> *"What is smart money actually doing?"*

AlphaTrace is a multi-agent research system that analyses SEC 13F filings for hedge funds (Citadel, Two Sigma, Tiger Global, Point72 etc.) and surfaces institutional-grade insights: position changes, alpha decay analysis, crowding risk, and a structured research hypothesis — delivered through a Bloomberg-terminal Streamlit UI.

---

## Live Demo

**Deployed URL:** `[your-cloud-run-url]`

---

## Quickstart (Local)

```bash
git clone https://github.com/your-repo/alphatrace && cd alphatrace
pip install -r requirements.txt
cp .env.example .env          # fill in GOOGLE_CLOUD_PROJECT + SEC_USER_AGENT
gcloud auth application-default login
streamlit run app.py
```

## Deploy to GCP Cloud Run

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/alphatrace
gcloud run deploy alphatrace \
  --image gcr.io/$PROJECT_ID/alphatrace \
  --platform managed --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

---

## The Three Steps

### Step 1 — Collect

The `DataCollector` agent retrieves data from **two external sources at runtime**. Nothing is hard-coded.

| Source | Method | Volume |
|--------|--------|--------|
| SEC EDGAR 13F API | REST + XML parse | ~3,200 holdings/filing for large funds |
| yfinance | Python API | Live prices + historical OHLCV for all tickers |

The agent: (1) resolves fund name to CIK via EDGAR search, (2) fetches the two most recent 13F-HR filing indexes, (3) downloads and parses the InfoTable XML for both quarters, (4) resolves CUSIP/issuer names to ticker symbols using SEC's `company_tickers.json`, (5) fetches live prices and sector data via yfinance.

**Code:** `tools/sec_edgar.py` — `search_fund_cik()`, `get_fund_filings()`, `fetch_13f_holdings()`  
**Code:** `tools/market_data.py` — `get_current_prices()`, `get_sector_breakdown()`  
**Agent:** `agents/collector_agent.py` — `collector_agent`

### Step 2 — Explore and Analyse

The `EDAAnalyst` agent performs dynamic exploratory analysis via a **parallel fan-out** of three concurrent sub-analyses. It never produces generic summaries — it surfaces specific quantified findings.

| Analysis | Function | Output |
|----------|----------|--------|
| PositionDeltaAnalyst | `_analyse_position_deltas()` | QoQ delta %, NEW/ADDED/REDUCED/EXITED per position |
| PriceCorrelationAnalyst | `_analyse_price_correlations()` | Return % since filing — alpha decay signal per ticker |
| CrowdingAnalyst | `_analyse_crowding()` | Concentration score 0–100, unwind risk level per position |

All three run via `asyncio.gather()` in `run_parallel_eda_analysis()`. The agent also invokes `execute_python_analysis()` to run agent-written pandas code for additional statistics (e.g. HHI concentration index).

**Code:** `agents/eda_agent.py` — `run_parallel_eda_analysis()`, `_analyse_position_deltas()`, `_analyse_price_correlations()`, `_analyse_crowding()`  
**Code:** `tools/code_executor.py` — `execute_python_analysis()`

### Step 3 — Hypothesize

The `HypothesisAnalyst` agent synthesises EDA findings into a grounded, evidence-backed research hypothesis. Every claim is derived from the collected data — no model-weight hallucination.

Output includes: hypothesis statement, executive summary, supporting evidence list (with specific figures), risk factors, crowding warnings, top-10 positions table, and a confidence score.

Example: *"Citadel is executing a diversified long-equity strategy in Q3 2024 with the largest disclosed position in NVDA ($4.2B). 12 new positions suggest conviction in recent tech rotation. EXTREME crowding in top 3 names elevates macro unwind risk."*

**Code:** `agents/hypothesis_agent.py` — `build_hypothesis_report()`  
**Schema:** `models/schemas.py` — `HypothesisReport`

---

## Core Requirements

| Requirement | Implementation | File |
|-------------|---------------|------|
| **Frontend** | Streamlit — Bloomberg-terminal dark UI | `app.py` |
| **Agent Framework** | Google ADK (`LlmAgent`, `AgentTool`, `Runner`, `InMemorySessionService`) | `agents/`, `agent_runner.py` |
| **Tool Calling** | 12+ tools: EDGAR search, filing fetch, XML parse, yfinance prices, code exec, 4 chart generators, 3 artifact writers | `tools/` |
| **Non-trivial Dataset** | SEC EDGAR 13F InfoTable XML — Citadel: 3,200+ positions. Never fully loaded into context; top-50 by value returned | `tools/sec_edgar.py::fetch_13f_holdings()` |
| **Multi-agent Pattern** | Orchestrator-as-router + 3 specialist AgentTools (collector, eda, hypothesis) — each has a distinct system prompt and responsibility | `agents/orchestrator.py` |
| **Deployed** | GCP Cloud Run, Vertex AI backend, Workload Identity auth | `Dockerfile` |
| **README** | This document — maps all three steps + all grab-bag items to exact file + function | `README.md` |

---

## Grab-Bag Electives (All 6 implemented)

| Elective | Implementation | File + Function |
|----------|---------------|-----------------|
| **Second data retrieval method** | Method 1: SEC EDGAR (REST API + XML). Method 2: yfinance (Python library API). Distinct protocols, distinct endpoints | `tools/sec_edgar.py`, `tools/market_data.py` |
| **Parallel execution** | `asyncio.gather()` runs PositionDelta + PriceCorrelation + Crowding analyses concurrently. Results awaited and merged | `agents/eda_agent.py::run_parallel_eda_analysis()` |
| **Artifacts** | Research memo → `.md`, holdings → `.csv`, EDA summary → `.json` written to `./outputs/` at runtime | `tools/artifacts.py::save_research_memo()`, `save_holdings_csv()`, `save_eda_summary()` |
| **Structured output** | 6 Pydantic models enforce schema at each pipeline stage. `HypothesisReport` is the final structured output | `models/schemas.py` — `HoldingRecord`, `PositionDelta`, `PriceCorrelation`, `CrowdingMetric`, `EDAResult`, `HypothesisReport` |
| **Data visualization** | 4 charts generated by matplotlib at runtime: top-holdings bar, QoQ delta diverging bar, crowding risk heatmap, alpha decay scatter | `tools/visualization.py::generate_top_holdings_bar()`, `generate_position_delta_chart()`, `generate_crowding_heatmap()`, `generate_returns_scatter()` |
| **Code execution** | Agent writes pandas/numpy/matplotlib Python and `execute_python_analysis()` runs it in a sandboxed `exec()` environment with restricted namespace | `tools/code_executor.py::execute_python_analysis()` |

---

## Architecture

```
User Query (e.g. "Analyse Citadel latest 13F for crowding risk")
    │
    ▼
OrchestratorAgent  [agents/orchestrator.py]
    │
    ├──► AgentTool(DataCollectorAgent)  [agents/collector_agent.py]
    │        ├── search_fund_cik()           SEC EDGAR CIK search
    │        ├── get_fund_filings()          Filing index (submissions API)
    │        ├── fetch_13f_holdings() ×2     InfoTable XML, current + prior quarter
    │        ├── get_current_prices()        yfinance batch prices
    │        └── get_sector_breakdown()      yfinance sector metadata
    │
    ├──► AgentTool(EDAAnalyst)  [agents/eda_agent.py]
    │        └── run_parallel_eda_analysis()
    │                 └── asyncio.gather(
    │                       _analyse_position_deltas()      ◄─ parallel
    │                       _analyse_price_correlations()   ◄─ parallel
    │                       _analyse_crowding()             ◄─ parallel
    │                     )
    │                 + generate_position_delta_chart()
    │                 + generate_crowding_heatmap()
    │                 + generate_returns_scatter()
    │                 + save_eda_summary() → ./outputs/
    │
    └──► AgentTool(HypothesisAnalyst)  [agents/hypothesis_agent.py]
             └── build_hypothesis_report()
                      ├── generate_top_holdings_bar()
                      ├── HypothesisReport (Pydantic structured output)
                      ├── save_research_memo() → ./outputs/*.md
                      └── save_holdings_csv()  → ./outputs/*.csv
```

---

## File Structure

```
alphatrace/
├── README.md
├── requirements.txt
├── Dockerfile
├── .env.example
├── config.py                 # Env config, known fund CIK map
├── app.py                    # Streamlit frontend
├── agent_runner.py           # Async ADK runner (Streamlit-safe)
├── models/
│   └── schemas.py            # 6 Pydantic schemas
├── tools/
│   ├── sec_edgar.py          # SEC EDGAR — Data Retrieval Method 1
│   ├── market_data.py        # yfinance — Data Retrieval Method 2
│   ├── code_executor.py      # Sandboxed Python execution
│   ├── visualization.py      # matplotlib chart generators
│   └── artifacts.py          # Disk artifact writers
├── agents/
│   ├── orchestrator.py       # Root orchestrator
│   ├── collector_agent.py    # Step 1: Collect
│   ├── eda_agent.py          # Step 2: EDA (parallel fan-out)
│   └── hypothesis_agent.py   # Step 3: Hypothesize
└── outputs/                  # Runtime artifacts (charts, memos, CSVs)
```

---

## Example Queries

```
"Analyse Citadel Advisors latest 13F for crowding risk and new positions"
"What did Tiger Global buy and sell this quarter?"
"Analyse Two Sigma for alpha decay — which entries are working?"
"What are Point72's highest-conviction adds in their latest filing?"
"Compare D.E. Shaw's current vs prior quarter positioning"
```

---

## Data Notes

- All 13F data is **public** — no API key required for SEC EDGAR
- Filings lag by **up to 45 days** post-quarter-end (noted as risk factor in every hypothesis)
- Ticker resolution: SEC `company_tickers.json` + yfinance fallback
- Top 50 positions by market value are returned per filing (full filings can be 3,000+ rows)
