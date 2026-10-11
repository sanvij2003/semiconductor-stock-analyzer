"""Week 1 Streamlit snapshot, peer comparison and growth/valuation analysis."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st

from analysis_tabs import render_growth, render_peers
from chart_presentation import EMPTY_FILTER_MESSAGE, build_ticker_colors, format_market_cap_label
from technical_tabs import render_returns, render_technicals


DATA_PATH = Path(__file__).resolve().parent / "data" / "fundamentals.csv"
NUMERIC_COLUMNS = [
    "Market Cap", "Price", "P/S", "P/E", "Forward P/E",
    "EPS This Y", "EPS Next Y", "Gross Margin", "Insider Own",
    "Relative Strength Index (14)", "52W High", "52W Low",
    "Perf YTD", "Perf 3Y", "Perf 5Y", "SMA50", "SMA200",
]


@st.cache_data(show_spinner=False, max_entries=4)
def load_fundamentals(path: str, modified_ns: int, size: int) -> pd.DataFrame:
    """The file signature participates in caching, so CSV updates invalidate it."""
    frame = pd.read_csv(path)
    if "Ticker" not in frame:
        raise ValueError("The fundamentals file needs a Ticker column.")
    frame["Ticker"] = frame["Ticker"].astype("string").str.strip()
    frame = frame.loc[frame["Ticker"].notna() & frame["Ticker"].ne("")].copy()
    if frame["Ticker"].duplicated().any():
        raise ValueError("The fundamentals file contains duplicate tickers.")
    for column in NUMERIC_COLUMNS:
        # Missing optional KPI columns remain visible as n/a, not an exception.
        if column not in frame:
            frame[column] = float("nan")
        frame[column] = pd.to_numeric(frame[column], errors="coerce").replace(
            [float("inf"), float("-inf")], float("nan")
        )
    return frame.sort_values("Ticker").reset_index(drop=True)


def finite_number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def format_number(value: object, prefix: str = "", suffix: str = "") -> str:
    number = finite_number(value)
    return "n/a" if number is None else f"{prefix}{number:,.2f}{suffix}"


def format_market_cap(value: object) -> str:
    number = finite_number(value)
    if number is None or number < 0:
        return "n/a"
    scale, suffix = (1e12, "T") if number >= 1e12 else (1e9, "B")
    return f"${number / scale:,.2f}{suffix}"


def format_high_distance(price: object, high: object) -> str:
    price_number, high_number = finite_number(price), finite_number(high)
    if price_number is None or high_number is None or high_number <= 0 or price_number < 0:
        return "n/a"
    distance = price_number / high_number - 1
    return f"{distance:+.2%}" if math.isfinite(distance) else "n/a"


def filter_companies(
    frame: pd.DataFrame, cap_range: tuple[float, float], tickers: list[str]
) -> pd.DataFrame:
    """Slider values are billions; the underlying Market Cap stays in dollars."""
    low, high = cap_range
    return frame.loc[
        frame["Market Cap"].between(low * 1e9, high * 1e9, inclusive="both")
        & frame["Ticker"].isin(tickers)
    ]


def snapshot_metrics(row: pd.Series) -> list[tuple[str, str]]:
    return [
        ("Market Cap", format_market_cap(row.get("Market Cap"))),
        ("Price", format_number(row.get("Price"), prefix="$")),
        ("P/S", format_number(row.get("P/S"))),
        ("P/E", format_number(row.get("P/E"))),
        ("Forward P/E", format_number(row.get("Forward P/E"))),
        ("EPS This Y", format_number(row.get("EPS This Y"), suffix="%")),
        ("EPS Next Y", format_number(row.get("EPS Next Y"), suffix="%")),
        ("Gross Margin", format_number(row.get("Gross Margin"), suffix="%")),
        ("Insider Own", format_number(row.get("Insider Own"), suffix="%")),
        ("RSI", format_number(row.get("Relative Strength Index (14)"))),
        ("% from 52-week high", format_high_distance(row.get("Price"), row.get("52W High"))),
    ]


def render_snapshot(filtered: pd.DataFrame) -> None:
    available = filtered["Ticker"].tolist()
    if not available:
        st.info(EMPTY_FILTER_MESSAGE)
        return
    if st.session_state.get("snapshot_ticker") not in available:
        st.session_state["snapshot_ticker"] = available[0]
    selected = st.selectbox("Pick a ticker", options=available, key="snapshot_ticker")
    row = filtered.loc[filtered["Ticker"].eq(selected)].iloc[0]
    company = row.get("Company")
    st.subheader(f"{selected} — {company}" if pd.notna(company) and str(company).strip() else selected)
    metrics = snapshot_metrics(row)
    for start in range(0, len(metrics), 4):
        group = metrics[start:start + 4]
        for column, (label, value) in zip(st.columns(len(group)), group):
            column.metric(label, value, border=True)
    missing_metrics = [label for label, value in metrics if value == "n/a"]
    if missing_metrics:
        st.info(
            f"{selected} doesn't have usable values for {', '.join(missing_metrics)} "
            "in this export, so those cards show n/a — the other metrics are still available."
        )
    with st.expander("How this is calculated", expanded=False):
        st.caption(
            "Growth, margin and ownership values are percentage points. "
            "% from 52-week high = (Price / 52W High − 1) × 100. "
            "Missing values are shown as n/a."
        )


def filtered_csv(frame: pd.DataFrame) -> bytes:
    """Export the filtered values as-is, without display rounding or rescaling."""
    return frame.to_csv(index=False, na_rep="").encode("utf-8")


def main() -> None:
    st.set_page_config(page_title="Semiconductor Stock Financial Analysis", layout="wide")
    st.title("Semiconductor Stock Financial Analysis")
    st.caption("Data as of Oct 10, 2026, from a Finviz Elite screener export")

    try:
        signature = DATA_PATH.stat()
        data = load_fundamentals(str(DATA_PATH), signature.st_mtime_ns, signature.st_size)
    except FileNotFoundError:
        st.error("data/fundamentals.csv was not found. Run python3 fetch_data.py to create it.")
        st.stop()
    except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
        st.error("The fundamentals CSV could not be loaded. Check that it is a valid CSV with unique tickers.")
        st.stop()

    tickers = data["Ticker"].tolist()
    caps = data.loc[data["Market Cap"].ge(0), "Market Cap"].dropna()
    with st.sidebar:
        st.header("Filter companies")
        if caps.empty:
            st.warning("No valid market caps are available.")
            bounds = (0.0, 1.0)
        else:
            # Round outwards, so the full default slider includes every known cap.
            lower = math.floor(float(caps.min()) / 1e9 * 100) / 100
            upper = math.ceil(float(caps.max()) / 1e9 * 100) / 100
            bounds = (lower, upper if upper > lower else lower + 0.01)
        cap_range = st.slider(
            "Market cap range", min_value=bounds[0], max_value=bounds[1],
            value=bounds, format=" ", disabled=caps.empty,
            key=f"cap_range_{signature.st_mtime_ns}_{signature.st_size}",
        )
        # Native printf formats cannot switch B/T per value; render compact
        # labels next to the unchanged numeric range control instead.
        from_label, to_label = st.columns(2)
        from_label.caption(f"From {format_market_cap_label(cap_range[0] * 1e9)}")
        to_label.caption(f"To {format_market_cap_label(cap_range[1] * 1e9)}")
        ticker_key = "ticker_filter_empty_is_all"
        if ticker_key not in st.session_state:
            st.session_state[ticker_key] = []
        else:
            st.session_state[ticker_key] = [
                ticker for ticker in st.session_state[ticker_key] if ticker in tickers
            ]
        chosen_tickers = st.multiselect(
            "Tickers", options=tickers, key=ticker_key,
            placeholder="All tickers", help="Leave empty to include all stocks; select tickers to narrow the results.",
        )

    filtered = filter_companies(data, cap_range, chosen_tickers or tickers)
    ticker_colors = build_ticker_colors(data["Ticker"])
    st.sidebar.caption(f"{len(filtered)} of {len(data)} companies match")
    st.sidebar.download_button(
        "Download filtered data",
        data=filtered_csv(filtered), file_name="semiconductor_filtered_data.csv",
        mime="text/csv", disabled=filtered.empty, on_click="ignore",
        help="Download all stocks matching your filters as CSV; dollars and percentage-point values stay unchanged.",
    )
    if data["Market Cap"].isna().any() or data["Market Cap"].lt(0).any():
        st.sidebar.caption("Companies without a valid market cap are excluded from the range filter.")

    snapshot_tab, peer_tab, growth_tab, technical_tab, returns_tab = st.tabs(
        ["Company Snapshot", "Peer Comparison", "Growth vs Valuation", "Technicals & Trend", "Long-term Returns"]
    )
    with snapshot_tab:
        render_snapshot(filtered)
    with peer_tab:
        render_peers(filtered, ticker_colors)
    with growth_tab:
        render_growth(filtered, ticker_colors)
    with technical_tab:
        render_technicals(filtered, ticker_colors)
    with returns_tab:
        render_returns(filtered, ticker_colors)


if __name__ == "__main__":
    main()
