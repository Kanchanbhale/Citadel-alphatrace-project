"""
SEC EDGAR API tools — Step 1 (Collect), Data Retrieval Method 1.
"""
from __future__ import annotations
import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

import requests

from config import EDGAR_BASE_URL, SEC_HEADERS, KNOWN_FUND_CIKS

_TICKER_MAP: dict[str, str] = {}

def _load_ticker_map() -> dict[str, str]:
    global _TICKER_MAP
    if _TICKER_MAP:
        return _TICKER_MAP
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=10,
        )
        data = r.json()
        for entry in data.values():
            name = entry.get("title", "").upper().strip()
            ticker = entry.get("ticker", "").upper().strip()
            if name and ticker:
                _TICKER_MAP[name] = ticker
                clean = re.sub(
                    r"\b(INC|CORP|LTD|CO|LLC|LP|PLC|NV|SA|AG|CLASS\s+[A-Z]|COM|ADR|ADS)\b",
                    "",
                    name,
                ).strip()
                _TICKER_MAP[clean] = ticker
    except Exception:
        pass
    return _TICKER_MAP

def _resolve_ticker(issuer_name: str) -> Optional[str]:
    tmap = _load_ticker_map()
    name = issuer_name.upper().strip()
    if name in tmap:
        return tmap[name]
    clean = re.sub(
        r"\b(INC|CORP|LTD|CO|LLC|LP|PLC|NV|SA|AG|CLASS\s+[A-Z]|COM|ADR|ADS)\b",
        "",
        name,
    ).strip()
    if clean in tmap:
        return tmap[clean]
    tokens = name.split()[:2]
    prefix = " ".join(tokens)
    for k, v in tmap.items():
        if k.startswith(prefix):
            return v
    return None

def search_fund_cik(fund_name: str) -> str:
    key = fund_name.lower().strip()
    for k, cik in KNOWN_FUND_CIKS.items():
        if k in key or key in k:
            return json.dumps({"cik": cik, "name": fund_name, "found": True})

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": f'"{fund_name}"',
        "forms": "13F-HR",
        "dateRange": "custom",
        "startdt": "2023-01-01",
    }
    try:
        r = requests.get(url, params=params, headers=SEC_HEADERS, timeout=12)
        hits = r.json().get("hits", {}).get("hits", [])
        if hits:
            src = hits[0].get("_source", {})
            cik = str(src.get("ciks", [None])[0] or "").zfill(10)
            name = src.get("display_names", [fund_name])[0]
            if cik and cik != "0000000000":
                return json.dumps({"cik": cik, "name": name, "found": True})
    except Exception:
        pass

    return json.dumps({"cik": None, "name": fund_name, "found": False})

def get_fund_filings(cik: str, num_filings: int = 2) -> str:
    cik_padded = str(cik).zfill(10)
    url = f"{EDGAR_BASE_URL}/submissions/CIK{cik_padded}.json"
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=12)
        data = r.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        acc_nums = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        docs = recent.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form in ("13F-HR", "13F-HR/A") and len(results) < num_filings:
                results.append({
                    "form_type": form,
                    "accession_number": acc_nums[i],
                    "filing_date": dates[i],
                    "primary_doc": docs[i] if i < len(docs) else "",
                })

        if not results:
            for f in data.get("filings", {}).get("files", []):
                try:
                    time.sleep(0.2)
                    r2 = requests.get(
                        EDGAR_BASE_URL + "/submissions/" + f["name"],
                        headers=SEC_HEADERS,
                        timeout=12,
                    )
                    d2 = r2.json()
                    f2s = d2.get("form", [])
                    a2s = d2.get("accessionNumber", [])
                    dt2s = d2.get("filingDate", [])
                    for i, fm in enumerate(f2s):
                        if fm in ("13F-HR", "13F-HR/A") and len(results) < num_filings:
                            results.append({
                                "form_type": fm,
                                "accession_number": a2s[i],
                                "filing_date": dt2s[i],
                                "primary_doc": "",
                            })
                    if results:
                        break
                except Exception:
                    pass

        return json.dumps({
            "fund_name": data.get("name", ""),
            "cik": cik_padded,
            "filings": results,
        })
    except Exception as e:
        return json.dumps({"error": str(e), "cik": cik})

def _parse_13f_xml(xml_text: str) -> list[dict]:
    holdings: list[dict] = []

    clean = re.sub(r' xmlns[^=]*="[^"]*"', "", xml_text)
    clean = re.sub(r' xsi:[^=]*="[^"]*"', "", clean)
    clean = re.sub(r'<(/?)[\w]+:', r'<\1', clean)

    root = ET.fromstring(clean)

    for tbl in root.findall(".//infoTable"):
        try:
            def t(tag: str) -> str:
                el = tbl.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            name = t("nameOfIssuer")
            if not name:
                continue

            cusip = t("cusip")
            value = t("value")
            pc = t("putCall")

            amt = tbl.find("shrsOrPrnAmt")
            shares = 0
            stype = "SH"
            if amt is not None:
                shares_el = amt.find("sshPrnamt")
                stype_el = amt.find("sshPrnamtType")
                shares = int((shares_el.text or "0").strip()) if shares_el is not None and shares_el.text else 0
                stype = (stype_el.text or "SH").strip() if stype_el is not None and stype_el.text else "SH"

            value_usd = int((value or "0").strip()) * 1000 if (value or "").strip() else 0

            holdings.append({
                "issuer_name": name,
                "cusip": cusip,
                "value_usd": value_usd,
                "shares": shares,
                "share_type": stype,
                "put_call": pc if pc else None,
                "ticker": _resolve_ticker(name),
            })
        except Exception:
            continue

    return holdings

def fetch_13f_holdings(cik: str, accession_number: str) -> str:
    cik_int = int(str(cik).lstrip("0") or "0")
    acc_dash = accession_number.strip()
    acc_flat = acc_dash.replace("-", "")

    candidates = [
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_flat}/infotable.xml",
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_flat}/form13fInfoTable.xml",
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_flat}/13F_InfoTable.xml",
    ]

    xml_text = None
    chosen_url = None

    for url in candidates:
        try:
            time.sleep(0.15)
            r = requests.get(url, headers=SEC_HEADERS, timeout=15)
            if r.status_code == 200 and "<informationTable" in r.text:
                xml_text = r.text
                chosen_url = url
                break
        except Exception:
            continue

    if xml_text is None:
        return json.dumps({
            "error": "Could not retrieve 13F XML",
            "cik": cik,
            "accession_number": accession_number,
        })

    try:
        holdings = _parse_13f_xml(xml_text)
        holdings.sort(key=lambda x: x.get("value_usd", 0), reverse=True)
        total_value = sum(h.get("value_usd", 0) for h in holdings)

        return json.dumps({
            "cik": str(cik).zfill(10),
            "accession_number": accession_number,
            "xml_url": chosen_url,
            "holdings": holdings[:50],
            "total_count": len(holdings),
            "total_value_usd": total_value,
        })
    except Exception as e:
        return json.dumps({
            "error": f"parse failed: {e}",
            "cik": cik,
            "accession_number": accession_number,
            "xml_url": chosen_url,
        })
