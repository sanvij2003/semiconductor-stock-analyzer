"""Native Streamlit rendering for the two Prompt 3 analysis tabs."""

import pandas as pd
import streamlit as st

from peer_analysis import (
    GROWTH, PERCENT_COLUMNS, RANKINGS, VALUATION, analyze_growth,
    growth_figure, ranked_peers, ranking_figure,
)
from chart_presentation import (
    EMPTY_FILTER_MESSAGE, GROWTH_CAPTION, RANKING_CAPTIONS, build_ticker_colors,
    format_market_cap_label,
)


def formatted_table(frame: pd.DataFrame, placeholder: str = "n/a") -> None:
    """Styler changes display only; underlying numeric values still sort numerically."""
    formats = {
        column: ("{:,.2f}%" if column in PERCENT_COLUMNS else "{:,.2f}")
        for column in frame.select_dtypes(include="number").columns
    }
    if "Market Cap" in frame:
        formats["Market Cap"] = format_market_cap_label
    if "Distance (P/E multiple)" in frame:
        formats["Distance (P/E multiple)"] = "{:+.2f}"
    st.dataframe(
        frame.style.format(formats, na_rep="n/a"), hide_index=True,
        width="stretch", placeholder=placeholder,
    )


def render_peers(filtered: pd.DataFrame, ticker_colors: dict[str, str] | None = None) -> None:
    st.subheader("Peer Comparison")
    if filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
        return
    if ticker_colors is None:
        ticker_colors = build_ticker_colors(filtered["Ticker"])
    st.caption("Click any table header to sort. Market caps use `$B`/`$T`; percentages are percentage points.")
    priority = ["Ticker", "Market Cap", "Price", "Forward P/E", "P/S", "EPS Next Y", "Gross Margin"]
    ordered = [column for column in priority if column in filtered]
    ordered += [column for column in filtered if column not in ordered]
    display_frame = filtered.loc[:, ordered].rename(columns={"Relative Strength Index (14)": "RSI"})
    formatted_table(display_frame)
    for start in (0, 2):
        for container, (metric, ascending) in zip(st.columns(2), RANKINGS[start:start + 2]):
            with container:
                ranked = ranked_peers(filtered, metric, ascending)
                if ranked.empty:
                    st.info(
                        f"We don't have {metric} values for these companies yet, so there's "
                        "nothing to rank — try selecting more tickers or a wider market cap range."
                    )
                    continue
                st.plotly_chart(
                    ranking_figure(ranked, metric, ticker_colors), width="stretch", key=f"ranking_{metric}",
                )
                st.caption(RANKING_CAPTIONS[metric])
                omitted = filtered.loc[~filtered["Ticker"].isin(ranked["Ticker"]), "Ticker"].tolist()
                if omitted:
                    st.caption(
                        f"{metric} isn't available for {', '.join(omitted)}; "
                        "they stay in the table but are left out of this ranking."
                    )


def render_growth(filtered: pd.DataFrame, ticker_colors: dict[str, str] | None = None) -> None:
    st.subheader("Growth vs Valuation")
    if filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
        return
    if ticker_colors is None:
        ticker_colors = build_ticker_colors(filtered["Ticker"])
    result = analyze_growth(filtered)
    if result.eligible.empty:
        st.info(
            "We can't draw this comparison with the current selection: EPS Next Y or "
            "Forward P/E is missing for these stocks — try more tickers or a wider range."
        )
    else:
        st.plotly_chart(growth_figure(result, ticker_colors), width="stretch", key="growth_valuation")
        st.caption(GROWTH_CAPTION)

    # Keep exclusions directly below the chart, including when there is no chart.
    if result.excluded.empty:
        st.caption("Excluded tickers: none.")
    else:
        st.write("**Excluded tickers (missing EPS Next Y or Forward P/E)**")
        st.dataframe(result.excluded, hide_index=True, width="stretch", placeholder="n/a")
    if result.fit_message:
        st.warning(f"{result.fit_message} Try selecting more companies to compare different growth values.")
    with st.expander("How this is calculated", expanded=False):
        if not result.fit_message:
            st.caption(
                f"Unweighted OLS fit across all {len(result.eligible)} eligible stocks: "
                f"Forward P/E = {result.intercept:.4f} + ({result.slope:.4f} × EPS Next Y). "
                "This descriptive fit is not a forecast; uncertainty intervals are not shown."
            )
        st.caption(
            "Distance = actual Forward P/E − trend-implied Forward P/E, in P/E multiple units. "
            "Positive (above) means priced richly for expected growth; negative (below) means priced lower. "
            "Excluded stocks and unavailable fits show n/a."
        )
    st.subheader("Distance from the trend line")
    formatted_table(result.distances)
