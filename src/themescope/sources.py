"""Small, replaceable adapters for the prototype's live data sources."""

from __future__ import annotations

import csv
import html
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36 ThemeScope/0.1"
TIMEOUT_SECONDS = 30


class RateLimited(RuntimeError):
    pass


_YAHOO_BLOCKED_HOSTS: set[str] = set()


def _request(url: str, accept: str = "*/*", user_agent: str | None = None) -> bytes:
    """Fetch a public source with TLS verification and bounded transient retries."""
    last_error: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent or USER_AGENT,
                "Accept": accept,
                "Accept-Language": "en-US,en;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                raise RateLimited(f"HTTP 429 from {url}; no immediate retry") from exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                break
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 1.5 * (attempt + 1)
            time.sleep(min(delay, 8))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"Source request failed for {url}: {last_error}") from last_error


def request_json(url: str, accept: str = "application/json", user_agent: str | None = None) -> Any:
    return json.loads(_request(url, accept, user_agent=user_agent).decode("utf-8-sig"))


def _text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


class _TableParser(HTMLParser):
    """Collect text cells without depending on a browser or HTML package."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_row = False
        self._in_cell = False
        self._cell_text = ""
        self._cells: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._in_row = True
            self._cells = []
        elif tag in ("th", "td") and self._in_row:
            self._in_cell = True
            self._cell_text = ""

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self._in_cell:
            self._cells.append(" ".join(self._cell_text.split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._cells:
                self.rows.append(self._cells)
            self._in_row = False


def _number(value: Any) -> float | None:
    if value is None:
        return None
    raw = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
    if raw in ("", "-", "N/A", "n/a"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _date_from_text(value: str) -> str | None:
    value = value.strip()
    for fmt in ("%m/%d/%Y", "%b %d, %Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _vaneck_holdings(theme: dict[str, Any]) -> dict[str, Any]:
    discovery_error = None
    try:
        page = html.unescape(_text(_request(theme["holdings_source"]["url"], "text/html")))
        match = re.search(rf"GetDataset/\?blockId=(\d+)&pageId=(\d+)&ticker={re.escape(theme['anchor'])}", page, flags=re.IGNORECASE)
        if not match:
            raise RuntimeError("VanEck holdings dataset link absent")
        block_id, page_id = match.groups()
        url = f"https://www.vaneck.com/Main/HoldingsBlock/GetDataset/?blockId={block_id}&pageId={page_id}&ticker={theme['anchor']}"
        data = request_json(url)
    except Exception as exc:
        discovery_error = str(exc)
        url = theme['holdings_source'].get('dataset_fallback_url')
        if not url:
            raise
        data = request_json(url)
    if not data.get('AsOfDate') or not data.get('Holdings'):
        raise RuntimeError('VanEck dataset lacks dated holdings')
    if any(item.get('Ticker') != theme['anchor'] for item in data['Holdings']):
        raise RuntimeError('VanEck dataset fund identity mismatch')
    rows = []
    for item in data.get("Holdings", []):
        ticker = str(item.get("Label") or item.get("HoldingTicker") or "").strip()
        if not ticker or str(item.get("AssetClass", "")).lower() not in ("stock", "equity"):
            continue
        rows.append(
            {
                "ticker": ticker,
                "company": str(item.get("HoldingName") or ticker).strip(),
                "weight_pct": _number(item.get("Weight")),
                "security_id": item.get("ISIN") or item.get("CUSIP") or item.get("FIGI"),
                "country": item.get("Country"),
            }
        )
    as_of = str(data.get("AsOfDate") or "")[:10] or None
    return {"as_of": as_of, "url": url, "rows": rows, "discovery_error": discovery_error}


def _first_trust_holdings(theme: dict[str, Any]) -> dict[str, Any]:
    page = _text(_request(theme["holdings_source"]["url"], "text/html"))
    parser = _TableParser()
    parser.feed(page)
    header_index = None
    for index, row in enumerate(parser.rows):
        normalized = [cell.lower() for cell in row]
        if "security name" in normalized and "identifier" in normalized and "weighting" in normalized:
            header_index = index
            break
    if header_index is None:
        raise RuntimeError("First Trust holdings table was not present in the returned page")
    match = re.search(
        r"Holdings of the Fund as of\s*([^<\r\n]+)", page, flags=re.IGNORECASE
    ) or re.search(r"Holdings as of\s*([^<\r\n]+)", page, flags=re.IGNORECASE)
    as_of = _date_from_text(html.unescape(match.group(1)).strip()) if match else None
    rows = []
    for row in parser.rows[header_index + 1 :]:
        if len(row) < 7:
            continue
        ticker = row[1].strip()
        if not ticker or ticker.startswith("$") or _number(row[6]) is None:
            continue
        rows.append(
            {
                "ticker": ticker,
                "company": row[0].strip(),
                "security_id": row[2].strip(),
                "classification": row[3].strip(),
                "weight_pct": _number(row[6]),
            }
        )
    return {"as_of": as_of, "url": theme["holdings_source"]["url"], "rows": rows}


def _ishares_holdings(theme: dict[str, Any]) -> dict[str, Any]:
    rows = list(csv.reader(io.StringIO(_text(_request(theme["holdings_source"]["url"], "text/csv")))))
    header_index = next(
        (i for i, row in enumerate(rows) if row and row[0].strip().lower() == "ticker"), None
    )
    if header_index is None:
        raise RuntimeError("iShares holdings CSV did not contain a Ticker header")
    header = [value.strip() for value in rows[header_index]]
    index = {key.lower(): i for i, key in enumerate(header)}
    as_of = None
    for row in rows[:header_index]:
        if len(row) >= 2 and row[0].strip().lower() == "fund holdings as of":
            as_of = _date_from_text(row[1].strip())
    results = []
    for row in rows[header_index + 1 :]:
        if len(row) < len(header):
            continue
        ticker = row[index["ticker"]].strip()
        if not ticker or ticker == "-":
            continue
        type_column = index.get("type", index.get("asset class"))
        results.append(
            {
                "ticker": ticker,
                "company": row[index["name"]].strip(),
                "security_type": row[type_column].strip() if type_column is not None else None,
                "sector": row[index["sector"]].strip(),
                "weight_pct": _number(row[index["weight (%)"]]),
                "security_id": None,
                "country": row[index["location"]].strip() if "location" in index else None,
            }
        )
    return {"as_of": as_of, "url": theme["holdings_source"]["url"], "rows": results}


def _xlsx_rows(raw: bytes) -> list[list[Any]]:
    """Read the simple tabular XLSX files used by State Street with stdlib only."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for item in root.findall("m:si", ns):
                shared_strings.append("".join(t.text or "" for t in item.findall(".//m:t", ns)))
        sheet_names = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )
        if not sheet_names:
            raise RuntimeError("SPDR workbook did not contain a worksheet")
        root = ET.fromstring(archive.read(sheet_names[0]))
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        output: list[list[Any]] = []
        for row in root.findall(".//m:sheetData/m:row", ns):
            cells: dict[int, Any] = {}
            for cell in row.findall("m:c", ns):
                address = cell.attrib.get("r", "")
                col_letters = re.match(r"[A-Z]+", address)
                if not col_letters:
                    continue
                col_index = 0
                for char in col_letters.group(0):
                    col_index = col_index * 26 + (ord(char) - 64)
                col_index -= 1
                kind = cell.attrib.get("t")
                if kind == "inlineStr":
                    value: Any = "".join(t.text or "" for t in cell.findall(".//m:t", ns))
                else:
                    raw_value = cell.find("m:v", ns)
                    value = raw_value.text if raw_value is not None else None
                    if kind == "s" and value is not None:
                        value = shared_strings[int(value)]
                    elif value is not None:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                cells[col_index] = value
            if cells:
                output.append([cells.get(i) for i in range(max(cells) + 1)])
        return output


def _spdr_holdings(theme: dict[str, Any]) -> dict[str, Any]:
    raw = _request(theme["holdings_source"]["url"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    table = _xlsx_rows(raw)
    as_of = None
    for row in table[:8]:
        if len(row) > 1 and str(row[0] or "").strip().lower() == "holdings:":
            text = str(row[1] or "")
            match = re.search(r"as of\s+(.+)", text, flags=re.IGNORECASE)
            if match:
                as_of = _date_from_text(match.group(1))
    header_index = next(
        (
            i
            for i, row in enumerate(table)
            if len(row) > 4
            and str(row[0] or "").strip().lower() == "name"
            and str(row[1] or "").strip().lower() == "ticker"
        ),
        None,
    )
    if header_index is None:
        raise RuntimeError("SPDR workbook did not contain the expected holdings columns")
    results = []
    for row in table[header_index + 1 :]:
        if len(row) < 5:
            continue
        ticker = str(row[1] or "").strip()
        if not ticker:
            continue
        results.append(
            {
                "ticker": ticker,
                "company": str(row[0] or ticker).strip(),
                "security_id": str(row[2] or "").strip() or None,
                "weight_pct": _number(row[4]),
            }
        )
    return {"as_of": as_of, "url": theme["holdings_source"]["url"], "rows": results}


HOLDINGS_PARSERS = {
    "vaneck_dataset": _vaneck_holdings,
    "first_trust_html": _first_trust_holdings,
    "ishares_csv": _ishares_holdings,
    "spdr_xlsx": _spdr_holdings,
}


def fetch_holdings(theme: dict[str, Any]) -> dict[str, Any]:
    method = theme["holdings_source"]["method"]
    if method not in HOLDINGS_PARSERS:
        raise ValueError(f"Unknown holdings parser: {method}")
    result = HOLDINGS_PARSERS[method](theme)
    result["retrieved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return result


def fetch_yahoo_chart(symbol: str, years: int = 2) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = int((now - timedelta(days=365 * years + 2)).timestamp())
    end = int(now.timestamp()) + 86400
    failures = []
    for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
        if host in _YAHOO_BLOCKED_HOSTS:
            failures.append(f'{host}: circuit open after HTTP 429 in this run')
            continue
        url = f"https://{host}/v8/finance/chart/{symbol}?period1={start}&period2={end}&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
        try:
            data = request_json(url)
            if not data.get('chart', {}).get('result'):
                raise RuntimeError(f'No chart result: {data.get("chart", {}).get("error")}')
            break
        except Exception as exc:
            if isinstance(exc, RateLimited):
                _YAHOO_BLOCKED_HOSTS.add(host)
            failures.append(str(exc))
    else:
        raise RuntimeError('; '.join(failures))
    chart = data.get("chart", {})
    if chart.get("error") or not chart.get("result"):
        raise RuntimeError(f"Yahoo chart returned no data for {symbol}: {chart.get('error')}")
    result = chart["result"][0]
    if result.get("meta", {}).get("symbol", "").upper() != symbol.upper():
        raise RuntimeError("Yahoo chart symbol identity mismatch")
    exchange_tz_name = result.get("meta", {}).get("exchangeTimezoneName") or "America/New_York"
    try:
        exchange_tz = ZoneInfo(exchange_tz_name)
    except Exception:
        exchange_tz = ZoneInfo("America/New_York")
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adjusted = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or []
    observations = []
    for i, stamp in enumerate(timestamps):
        close = quote.get("close", [None] * len(timestamps))[i]
        volume = quote.get("volume", [None] * len(timestamps))[i]
        adj_close = adjusted[i] if i < len(adjusted) else None
        observations.append(
            {
                "date": datetime.fromtimestamp(stamp, exchange_tz).date().isoformat(),
                "close": float(close) if close is not None else None,
                "adj_close": float(adj_close) if adj_close is not None else None,
                "volume": float(volume) if volume is not None else None,
                "missing": close is None or adj_close is None or volume is None,
            }
        )
    return {
        "symbol": symbol,
        "fallback_attempts": failures,
        "url": url,
        "retrieved_at": now.isoformat(timespec="seconds"),
        "meta": result.get("meta", {}),
        "events": result.get("events", {}),
        "observations": observations,
    }


def fetch_nasdaq_summary(symbol: str) -> dict[str, Any]:
    url = f"https://api.nasdaq.com/api/quote/{symbol}/summary?assetclass=stocks"
    data = request_json(url)
    response = data.get("data") or {}
    summary = response.get("summaryData") or {}
    if not summary:
        raise RuntimeError(f"Nasdaq quote summary returned no summary fields for {symbol}")
    def value(key: str) -> str | None:
        item = summary.get(key)
        return item.get("value") if isinstance(item, dict) else None
    return {
        "symbol": symbol,
        "url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "company_name": response.get("companyName"),
        "exchange": value("Exchange"),
        "sector": value("Sector"),
        "industry": value("Industry"),
        "market_cap_raw": value("MarketCap"),
        "market_cap_usd": _number(value("MarketCap")),
        "timestamp_note": "Nasdaq's summary response does not publish a separate market-cap timestamp; this is a current quote-summary retrieval, with retrieval time recorded.",
    }


def fetch_sec_latest_annual(cik: int | str) -> dict[str, Any]:
    """Check the latest SEC annual report form for an issuer at regeneration time."""
    cik_text = str(int(cik)).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_text}.json"
    data = request_json(url, user_agent="ThemeScope/0.1")
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    accepted = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
    choices = []
    for index, form in enumerate(forms):
        if form not in accepted or index >= len(dates):
            continue
        filing_date = dates[index]
        if not filing_date:
            continue
        accession = accessions[index] if index < len(accessions) else ""
        document = documents[index] if index < len(documents) else ""
        archive_url = None
        if accession and document:
            archive_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession.replace('-', '')}/{document}"
            )
        choices.append((filing_date, form, accession, archive_url))
    if not choices:
        raise RuntimeError(f"SEC submissions data did not contain a recent annual report for CIK {cik_text}")
    filing_date, form, accession, archive_url = max(choices, key=lambda item: (item[0], item[1]))
    return {
        "cik": int(cik),
        "url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_annual_form": form,
        "latest_annual_filed_date": filing_date,
        "accession_number": accession,
        "filing_url": archive_url,
    }
