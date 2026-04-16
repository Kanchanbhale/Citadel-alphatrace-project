"""Central configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Google Cloud ──────────────────────────────────────────────────────────────
PROJECT_ID      = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION        = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL           = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Artifacts ─────────────────────────────────────────────────────────────────
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "./outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ── SEC EDGAR ─────────────────────────────────────────────────────────────────
EDGAR_BASE_URL   = "https://data.sec.gov"
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
SEC_USER_AGENT   = os.getenv("SEC_USER_AGENT", "AlphaTrace Research alphatrace@example.com")
SEC_HEADERS      = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}

# ── Known flagship hedge funds with pre-verified CIKs ─────────────────────────
# Saves an EDGAR lookup round-trip for common queries.
KNOWN_FUND_CIKS: dict[str, str] = {
    "citadel":              "0001423298",
    "citadel advisors":     "0001423298",
    "bridgewater":          "0001350694",
    "two sigma":            "0001424322",
    "renaissance":          "0001037389",
    "ren tech":             "0001037389",
    "point72":              "0001603466",
    "millennium":           "0001273931",
    "d.e. shaw":            "0001009207",
    "de shaw":              "0001009207",
    "tiger global":         "0001167483",
    "ackman":               "0001336528",
    "pershing square":      "0001336528",
    "appaloosa":            "0001656456",
    "druckenmiller":        "0001536411",
    "duquesne":             "0001536411",
    "baupost":              "0001061768",
    "third point":          "0001040273",
    "dan loeb":             "0001040273",
    "viking global":        "0001103804",
    "coatue":               "0001336917",
    "whale rock":           "0001613160",
}
