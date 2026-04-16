"""
Data Collection Agent — Step 1 (Collect).

Responsibilities:
  • Search for hedge fund CIK on SEC EDGAR
  • Retrieve two most recent 13F-HR filings
  • Parse and return holdings + filing metadata
  • Fetch current market prices for top holdings (second data source)
"""
from google.adk.agents import LlmAgent

from config import MODEL
from tools.sec_edgar import search_fund_cik, get_fund_filings, fetch_13f_holdings
from tools.market_data import get_current_prices, get_sector_breakdown

COLLECTOR_INSTRUCTION = """
You are a specialized SEC data collection agent for AlphaTrace, an institutional
research platform. Your sole job is to collect raw 13F filing data from the SEC
EDGAR public API and supplement it with current market prices from yfinance.

## Workflow

1. Call `search_fund_cik` with the fund name to get its CIK.
2. Call `get_fund_filings` to list the two most recent 13F-HR filings.
3. Call `fetch_13f_holdings` for each of the two filings (current + prior quarter).
4. Extract all tickers from the holdings and call `get_current_prices`.
5. Call `get_sector_breakdown` with the ticker list.

## Output format

Return a JSON object with EXACTLY these keys:
{
  "fund_name": string,
  "cik": string,
  "current_filing": {
    "accession_number": string,
    "filing_date": string,
    "holdings": [...],     // top 50 by value
    "total_count": int,
    "total_value_usd": float
  },
  "prior_filing": {
    "accession_number": string,
    "filing_date": string,
    "holdings": [...]
  },
  "current_prices": { ticker: price },
  "sector_map": { ticker: sector }
}

## Rules
- Always retrieve BOTH filings so the EDA agent can compute deltas.
- If the fund is not found, return {"error": "Fund not found", "fund_name": ...}.
- Do NOT analyse the data — just collect and return it.
- The SEC User-Agent header is already set in the tools; you do not need to worry about it.
"""

collector_agent = LlmAgent(
    name="data_collector",
    model=MODEL,
    description=(
        "Fetches SEC 13F filings and live market data for a given hedge fund. "
        "Returns raw holdings for two quarters plus current prices and sector map."
    ),
    instruction=COLLECTOR_INSTRUCTION,
    tools=[
        search_fund_cik,
        get_fund_filings,
        fetch_13f_holdings,
        get_current_prices,
        get_sector_breakdown,
    ],
)
