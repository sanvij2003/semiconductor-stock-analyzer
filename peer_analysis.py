"""Pure peer-ranking, regression and Plotly figure helpers."""

from dataclasses import dataclass
import math

import pandas as pd
import plotly.graph_objects as go

from chart_presentation import AXIS_LABELS, RANKING_TITLES, ticker_color


GROWTH = "EPS Next Y"
VALUATION = "Forward P/E"
REQUIRED = (GROWTH, VALUATION)
RANKINGS = ((VALUATION, True), ("P/S", True), ("Gross Margin", False), (GROWTH, False))
PERCENT_COLUMNS = {
    "Perf YTD", "Perf 3Y", "Perf 5Y", "EPS This Y", GROWTH,
    "Gross Margin", "Insider Own", "SMA50", "SMA200",
}


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace(
        [float("inf"), float("-inf")], float("nan")
    )


def ranked_peers(frame: pd.DataFrame, metric: str, ascending: bool) -> pd.DataFrame:
    ranked = frame[["Ticker"]].copy()
    ranked[metric] = numeric(frame.get(metric, pd.Series(index=frame.index, dtype=float)))
    return ranked.dropna(subset=[metric]).sort_values([metric, "Ticker"], ascending=[ascending, True])


@dataclass
class GrowthAnalysis:
    eligible: pd.DataFrame
    excluded: pd.DataFrame
    distances: pd.DataFrame
    slope: float | None
    intercept: float | None
    fit_message: str


def analyze_growth(frame: pd.DataFrame) -> GrowthAnalysis:
    work = frame.reset_index(drop=True).copy()
    for column in (*REQUIRED, "Market Cap"):
        work[column] = numeric(work.get(column, pd.Series(index=work.index, dtype=float)))
    reasons = []
    for _, row in work.iterrows():
        invalid = []
        for column in REQUIRED:
            if pd.isna(row[column]):
                invalid.append(f"{column}: missing or nonfinite")
        reasons.append("; ".join(invalid))
    mask = pd.Series([not reason for reason in reasons], index=work.index, dtype=bool)
    eligible = work.loc[mask].copy()
    excluded = work.loc[~mask, ["Ticker"]].copy()
    excluded["Reason"] = [reason for reason in reasons if reason]
    slope = intercept = None
    if len(eligible) < 2:
        message = "A trend line needs at least two eligible stocks."
    elif eligible[GROWTH].nunique() < 2:
        message = "A trend line needs at least two distinct EPS Next Y values."
    else:
        try:
            xs, ys = eligible[GROWTH].tolist(), eligible[VALUATION].tolist()
            x_mean, y_mean = math.fsum(xs) / len(xs), math.fsum(ys) / len(ys)
            denominator = math.fsum((x - x_mean) ** 2 for x in xs)
            slope = math.fsum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator
            intercept = y_mean - slope * x_mean
            if not all(math.isfinite(value) for value in (slope, intercept)):
                raise ValueError("Nonfinite fit")
            message = ""
        except (OverflowError, ValueError, ZeroDivisionError):
            slope = intercept = None
            message = "These values cannot produce a numerically stable trend line."

    distances = work[["Ticker", GROWTH, VALUATION]].copy()
    distances["Trend-implied Forward P/E"] = float("nan")
    distances["Distance (P/E multiple)"] = float("nan")
    distances["Interpretation"] = ["n/a — excluded" if reason else "n/a — no fitted trend" for reason in reasons]
    if slope is not None:
        predicted = slope * eligible[GROWTH] + intercept
        residual = eligible[VALUATION] - predicted
        distances.loc[mask, "Trend-implied Forward P/E"] = predicted
        distances.loc[mask, "Distance (P/E multiple)"] = residual
        for index in eligible.index:
            value = float(residual.loc[index])
            if math.isclose(value, 0, abs_tol=1e-9):
                label = "On trend"
            elif value > 0:
                label = "Above — priced richly for expected growth"
            else:
                label = "Below — priced lower for expected growth"
            distances.loc[index, "Interpretation"] = label
    return GrowthAnalysis(eligible, excluded, distances, slope, intercept, message)


def ranking_figure(
    ranked: pd.DataFrame, metric: str, ticker_colors: dict[str, str] | None = None,
) -> go.Figure:
    percent = metric in PERCENT_COLUMNS
    suffix = "%" if percent else "×"
    figure = go.Figure(go.Bar(
        x=ranked[metric].tolist(), y=ranked["Ticker"].tolist(), orientation="h",
        marker_color=[ticker_color(ticker, ticker_colors) for ticker in ranked["Ticker"]],
        hovertemplate=f"%{{y}}<br>{metric}: %{{x}}{suffix}<extra></extra>",
    ))
    figure.update_layout(
        title=RANKING_TITLES.get(metric, metric), height=max(320, 24 * len(ranked) + 110),
        showlegend=False,
        xaxis_title=AXIS_LABELS.get(metric, f"{metric} ({'%' if percent else '×'})"),
        yaxis_title="Ticker",
    )
    figure.update_yaxes(categoryorder="array", categoryarray=ranked["Ticker"].tolist(), autorange="reversed")
    figure.update_xaxes(ticksuffix=suffix, rangemode="tozero")
    return figure


def growth_figure(
    result: GrowthAnalysis, ticker_colors: dict[str, str] | None = None,
) -> go.Figure:
    eligible = result.eligible
    figure = go.Figure()
    if eligible.empty:
        return figure
    # Missing/invalid size data must not exclude an otherwise plottable stock.
    sizes = eligible["Market Cap"].clip(lower=0).fillna(0).tolist()
    largest = max(sizes)
    figure.add_trace(go.Scatter(
        x=eligible[GROWTH].tolist(), y=eligible[VALUATION].tolist(),
        mode="markers+text", text=eligible["Ticker"].tolist(), textposition="top center",
        cliponaxis=False,
        name="Stocks", showlegend=False,
        customdata=eligible[["Ticker", "Market Cap"]].values.tolist(),
        marker=dict(size=sizes, sizemode="area", sizeref=2 * largest / 60**2 if largest else 1,
                    sizemin=3, color=[ticker_color(ticker, ticker_colors) for ticker in eligible["Ticker"]]),
        hovertemplate="<b>%{customdata[0]}</b><br>EPS Next Y: %{x}%"
                      "<br>Forward P/E: %{y}×<br>Market Cap: $%{customdata[1]:,}<extra></extra>",
    ))
    if result.slope is not None:
        endpoints = [float(eligible[GROWTH].min()), float(eligible[GROWTH].max())]
        figure.add_trace(go.Scatter(
            x=endpoints, y=[result.slope * x + result.intercept for x in endpoints],
            mode="lines", name="OLS fitted trend", line=dict(color="#475569"),
            hovertemplate="Growth: %{x}%<br>Trend Forward P/E: %{y}×<extra></extra>",
        ))
    figure.update_layout(
        title="Expected EPS growth vs. Forward P/E", height=520,
        xaxis_title=AXIS_LABELS[GROWTH], yaxis_title=AXIS_LABELS[VALUATION],
        legend=dict(orientation="h", y=1.12),
    )
    figure.update_xaxes(ticksuffix="%")
    figure.update_yaxes(autorange=True, ticksuffix="×")
    return figure
