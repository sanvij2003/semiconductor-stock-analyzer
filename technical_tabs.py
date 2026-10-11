"""New tab presentation, isolated from the existing snapshot and peer views."""

import pandas as pd
import streamlit as st

from chart_presentation import EMPTY_FILTER_MESSAGE
from trend_charts import (
    RETURN_COLUMNS, RSI, range_data, range_figure, returns_data, returns_figure,
    rsi_data, rsi_figure, trend_data, trend_figure,
)


CAPTIONS = (
    "Upper-right points are Uptrend, lower-left points are Downtrend, and the other quadrants or zero-boundary points are Mixed, with both axes showing price distance from a moving average in percent.",
    "RSI bars rank stocks from highest to lowest, with the dashed 30 and 70 lines marking the usual oversold and overbought thresholds.",
    "A position of 0% is the 52-week low and 100% is the high, with larger values ranked first and any prices outside that range left unclipped.",
    "Grouped bars compare YTD, three-year and five-year returns in percent, ranked by five-year return with missing five-year values last and missing bars left as gaps.",
)


def _missing_message(frame: pd.DataFrame, available: pd.DataFrame, metric: str) -> None:
    missing = sorted(set(frame.Ticker) - set(available.Ticker))
    if missing:
        st.caption(f"{metric} unavailable for: {', '.join(missing)} (n/a).")


def render_technicals(filtered: pd.DataFrame, colors: dict[str, str]) -> None:
    st.subheader("Technicals & Trend")
    if filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
        return
    points, groups, missing = trend_data(filtered)
    if points.empty:
        st.info("No stocks have both SMA50 and SMA200 values available for this chart.")
    else:
        st.plotly_chart(trend_figure(points, colors), width="stretch", key="technical_trend")
        st.caption(CAPTIONS[0])
    st.dataframe(groups, hide_index=True, width="stretch", placeholder="n/a")
    if missing:
        st.caption(f"Missing SMA data: {', '.join(missing)} (n/a); these stocks cannot be assigned a trend group.")
    rsi = rsi_data(filtered)
    if rsi.empty:
        st.info("No RSI values are available for the selected stocks.")
    else:
        st.plotly_chart(rsi_figure(rsi, colors), width="stretch", key="technical_rsi")
        st.caption(CAPTIONS[1])
    _missing_message(filtered, rsi, "RSI")
    positions = range_data(filtered)
    if positions.empty:
        st.info("No selected stocks have a price and valid 52-week low/high range.")
    else:
        st.plotly_chart(range_figure(positions, colors), width="stretch", key="technical_range")
        st.caption(CAPTIONS[2])
    _missing_message(filtered, positions, "52-week position (missing inputs or high not above low)")


def render_returns(filtered: pd.DataFrame, colors: dict[str, str]) -> None:
    st.subheader("Long-term Returns")
    if filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
        return
    returns = returns_data(filtered)
    if returns[list(RETURN_COLUMNS)].isna().all().all():
        st.info("No historical return values are available for the selected stocks.")
        return
    st.plotly_chart(returns_figure(returns, colors), width="stretch", key="historical_returns")
    st.caption(CAPTIONS[3])
