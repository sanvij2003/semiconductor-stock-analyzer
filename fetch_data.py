"""Finviz Elite CSV data layer. Run from the project with python3 fetch_data.py.

Set FINVIZ_EXPORT_URL to the export URL containing auth={FINVIZ_API_KEY}.
Only FINVIZ_API_KEY is secret. No dashboard is created by this module.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import pandas as pd
import requests


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
PERCENT_COLUMNS = (
    "Perf YTD", "Perf 3Y", "Perf 5Y", "EPS This Y", "EPS Next Y",
    "Gross Margin", "Insider Own", "SMA50", "SMA200",
)
HEADER_ALIASES = {
    "52-Week Range": "52W Range",
    "50-Day Simple Moving Average": "SMA50",
    "200-Day Simple Moving Average": "SMA200",
    "Performance (YTD)": "Perf YTD",
    "Performance (3 Years)": "Perf 3Y",
    "Performance (5 Years)": "Perf 5Y",
    "EPS Growth This Year": "EPS This Y",
    "EPS Growth Next Year": "EPS Next Y",
    "Insider Ownership": "Insider Own",
}
REDIRECT_CODES = {301, 302, 303, 307, 308}


class DataError(Exception):
    """Safe error text: never include URLs, responses, or credentials."""


def validate_url(url: str) -> None:
    """Keep the API key on HTTPS Finviz endpoints, including redirects."""
    try:
        parts = urlsplit(url)
        valid = (
            parts.scheme == "https"
            and parts.hostname in {"finviz.com", "www.finviz.com", "elite.finviz.com"}
            and parts.port in {None, 443}
            and parts.username is None
            and parts.password is None
        )
    except ValueError:
        valid = False
    if not valid:
        raise DataError("Use an HTTPS Finviz export URL without embedded credentials.")


def authenticated_url(template: str, key: str) -> str:
    validate_url(template)
    parts = urlsplit(template)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    auth = [value for name, value in pairs if name == "auth"]
    if auth != ["{FINVIZ_API_KEY}"]:
        raise DataError("The export URL must contain exactly auth={FINVIZ_API_KEY}.")
    pairs = [(name, key if name == "auth" else value) for name, value in pairs]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), ""))


def wait_for_request_slot() -> None:
    """Space requests by 0.6s: at most 9 requests in any 5-second window.

    A shared lock also covers redirects and concurrent runs of this project.
    Lock state lives outside the repository and contains no credentials.
    """
    project_id = hashlib.sha256(str(PROJECT_DIR).encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"finviz-rate-{project_id}.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        lock.seek(0)
        saved = lock.read().strip()
        try:
            previous = float(saved) if saved else 0.0
        except ValueError:
            previous = 0.0
        now = time.monotonic()
        if previous <= now:
            time.sleep(max(0.0, 0.6 - (now - previous)))
        lock.seek(0)
        lock.truncate()
        lock.write(str(time.monotonic()))
        lock.flush()


def download_export(template: str, key: str) -> bytes:
    url = authenticated_url(template, key)
    # Follow redirects explicitly so every hop uses the rate limiter.
    with requests.Session() as session:
        session.headers["User-Agent"] = "SemiconductorStockFinancialAnalysis/1.0"
        for _ in range(11):
            validate_url(url)
            wait_for_request_slot()
            try:
                response = session.get(url, allow_redirects=False, timeout=(10, 60))
            except requests.RequestException:
                raise DataError("Finviz download failed. Check connectivity and try again.") from None
            if response.status_code in REDIRECT_CODES:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise DataError("Finviz returned a redirect without a destination.")
                url = urljoin(url, location)
                continue
            if response.status_code != 200:
                status = response.status_code
                response.close()
                raise DataError(
                    f"Finviz returned HTTP {status}. Check the export URL and Elite access."
                )
            content = response.content
            response.close()
            if not content:
                raise DataError("Finviz returned an empty file.")
            if key.encode() in content:
                raise DataError("Finviz returned a response containing credentials; nothing was saved.")
            return content
    raise DataError("Finviz exceeded the allowed number of redirects.")


def parse_export(content: bytes) -> pd.DataFrame:
    try:
        frame = pd.read_csv(
            io.BytesIO(content), encoding="utf-8-sig",
            keep_default_na=False, na_values=[""],
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise DataError("Finviz did not return a valid UTF-8 CSV export.") from None
    frame.columns = frame.columns.str.strip()
    frame = frame.rename(columns=HEADER_ALIASES)
    if frame.columns.duplicated().any():
        raise DataError("The CSV contains duplicate column names.")
    required = {"Market Cap", "52W Range", *PERCENT_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        # Do not echo remote response content (including arbitrary header text).
        raise DataError("The CSV is missing required assignment columns. Check export settings.")
    return frame


def numeric_column(series: pd.Series, column: str) -> pd.Series:
    try:
        result = pd.to_numeric(series, errors="raise")
    except (ValueError, TypeError):
        raise DataError(f"Column '{column}' contains non-numeric values.") from None
    if result.isin([float("inf"), float("-inf")]).any():
        raise DataError(f"Column '{column}' contains non-finite values.")
    return result


def clean_export(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy().replace(r"^\s*$", pd.NA, regex=True)
    cleaned = cleaned.drop(columns=["No."], errors="ignore")
    cleaned["Market Cap"] = numeric_column(cleaned["Market Cap"], "Market Cap") * 1_000_000
    # These are already percentage points; never divide/multiply by 100.
    # SMA50/SMA200 are price distances (%) from MAs, not MA prices.
    for column in PERCENT_COLUMNS:
        # Some live Finviz exports include a trailing % character.
        # Removing that display suffix does not change the numeric scale.
        values = cleaned[column].astype("string").str.strip().str.removesuffix("%").str.strip()
        cleaned[column] = numeric_column(values, column)
    ranges = cleaned["52W Range"].astype("string")
    bounds = ranges.str.extract(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$")
    if (ranges.notna() & bounds[0].isna()).any():
        raise DataError("Column '52W Range' contains an invalid low-high range.")
    cleaned["52W Low"] = numeric_column(bounds[0], "52W Low")
    cleaned["52W High"] = numeric_column(bounds[1], "52W High")
    if (cleaned["52W Low"] > cleaned["52W High"]).any():
        raise DataError("Column '52W Range' contains a low greater than its high.")
    return cleaned


def atomic_write(path: Path, content: bytes) -> None:
    """Replace a complete file without leaving partial downloads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        try:
            handle.write(content)
            handle.close()
            temp_path.replace(path)
        finally:
            temp_path.unlink(missing_ok=True)


def fetch_data(template: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    key = os.environ.get("FINVIZ_API_KEY", "").strip()
    if not key:
        raise DataError("Add FINVIZ_API_KEY in Replit Secrets before running the download.")
    content = download_export(template, key)
    raw_frame = parse_export(content)
    atomic_write(data_dir / "raw_export.csv", content)
    cleaned = clean_export(raw_frame)
    atomic_write(data_dir / "fundamentals.csv", cleaned.to_csv(index=False, na_rep="").encode("utf-8"))
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and clean the Finviz Elite CSV export.")
    parser.add_argument(
        "--url", default=os.environ.get("FINVIZ_EXPORT_URL"),
        help="Finviz export URL with auth={FINVIZ_API_KEY}; defaults to FINVIZ_EXPORT_URL.",
    )
    args = parser.parse_args()
    if not args.url:
        print("Missing export URL. Set FINVIZ_EXPORT_URL or pass --url with auth={FINVIZ_API_KEY}.",
              file=sys.stderr)
        return 1
    try:
        cleaned = fetch_data(args.url)
    except DataError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Exception:
        # Third-party exception strings/tracebacks can contain the authenticated URL.
        print("Data processing failed. No credentials were logged.", file=sys.stderr)
        return 1
    print("Saved data/raw_export.csv and data/fundamentals.csv")
    print("\nFirst 5 rows:")
    print(cleaned.head(5).to_string(index=False))
    print("\nColumn names:")
    print(cleaned.columns.tolist())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
