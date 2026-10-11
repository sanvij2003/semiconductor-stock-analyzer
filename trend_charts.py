"""Technical indicators and historical returns; source values stay unchanged."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from chart_presentation import ticker_color
from peer_analysis import numeric


RSI = "Relative Strength Index (14)"
RETURN_COLUMNS = ("Perf YTD", "Perf 3Y", "Perf 5Y")
GROUPS = ("Uptrend", "Downtrend", "Mixed")


def indicator_frame(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    work = frame[["Ticker"]].copy()
    for column in columns:
        work[column] = numeric(frame.get(column, pd.Series(index=frame.index, dtype=float)))
    return work


def trend_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    work = indicator_frame(frame, ("SMA200", "SMA50"))
    available = work[["SMA200", "SMA50"]].notna().all(axis=1)
    points = work.loc[available].copy()
    points["Group"] = "Mixed"
    points.loc[points.SMA200.gt(0) & points.SMA50.gt(0), "Group"] = "Uptrend"
    points.loc[points.SMA200.lt(0) & points.SMA50.lt(0), "Group"] = "Downtrend"
    groups = pd.DataFrame([
        {"Group": group, "Tickers": ", ".join(sorted(points.loc[points.Group.eq(group), "Ticker"])) or "n/a"}
        for group in GROUPS
    ])
    return points, groups, sorted(work.loc[~available, "Ticker"].tolist())


def rsi_data(frame: pd.DataFrame) -> pd.DataFrame:
    return indicator_frame(frame, (RSI,)).dropna(subset=[RSI]).sort_values(
        [RSI, "Ticker"], ascending=[False, True]
    )


def range_data(frame: pd.DataFrame) -> pd.DataFrame:
    work = indicator_frame(frame, ("Price", "52W Low", "52W High"))
    valid = work[["Price", "52W Low", "52W High"]].notna().all(axis=1)
    valid &= work["52W High"].gt(work["52W Low"])
    work = work.loc[valid].copy()
    work["52W Position"] = (work.Price - work["52W Low"]) / (
        work["52W High"] - work["52W Low"]
    ) * 100
    # Keep prices outside the saved range visible rather than clamping them.
    return work.sort_values(["52W Position", "Ticker"], ascending=[False, True])


def returns_data(frame: pd.DataFrame) -> pd.DataFrame:
    return indicator_frame(frame, RETURN_COLUMNS).sort_values(
        ["Perf 5Y", "Ticker"], ascending=[False, True], na_position="last"
    )


def _axis_limits(values: pd.Series) -> list[float]:
    low, high = min(0.0, float(values.min())), max(0.0, float(values.max()))
    low = low if low < 0 else -max(high * .15, 1)
    high = high if high > 0 else max(abs(low) * .15, 1)
    padding = (high - low) * .12
    return [low - padding, high + padding]


def trend_figure(points: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    figure = go.Figure(go.Scatter(
        x=points.SMA200.tolist(), y=points.SMA50.tolist(),
        mode="markers+text", text=points.Ticker.tolist(), textposition="top center",
        cliponaxis=False, marker={"size": 10, "color": [ticker_color(t, colors) for t in points.Ticker]},
        hovertemplate="%{text}<br>SMA200 distance: %{x:.2f}%<br>SMA50 distance: %{y:.2f}%<extra></extra>",
    ))
    x_limits, y_limits = _axis_limits(points.SMA200), _axis_limits(points.SMA50)
    figure.add_vline(x=0, line_color="gray", line_dash="dash")
    figure.add_hline(y=0, line_color="gray", line_dash="dash")
    for label, x, y in [
        ("Uptrend", x_limits[1] / 2, y_limits[1] * .85),
        ("Downtrend", x_limits[0] / 2, y_limits[0] * .75),
        ("Mixed", x_limits[0] / 2, y_limits[1] * .85),
        ("Mixed", x_limits[1] / 2, y_limits[0] * .75),
    ]:
        figure.add_annotation(
            x=x, y=y, text=label, showarrow=False,
            font={"color": "gray", "size": 12}, bgcolor="rgba(255,255,255,0.8)",
        )
    figure.update_layout(
        title="Price distance from 50-day and 200-day moving averages", height=550,
        showlegend=False, margin={"t": 65, "b": 65},
        xaxis={"title": "SMA200 — price distance from moving average (%)", "ticksuffix": "%", "range": x_limits},
        yaxis={"title": "SMA50 — price distance from moving average (%)", "ticksuffix": "%", "range": y_limits},
    )
    return figure


def indicator_bar(
    frame: pd.DataFrame, metric: str, title: str, axis: str, colors: dict[str, str]
) -> go.Figure:
    figure = go.Figure(go.Bar(
        x=frame[metric].tolist(), y=frame.Ticker.tolist(), orientation="h",
        marker_color=[ticker_color(t, colors) for t in frame.Ticker],
        customdata=frame.Ticker.tolist(),
        hovertemplate="%{customdata}<br>" + axis + ": %{x:.2f}<extra></extra>",
    ))
    figure.update_layout(
        title=title, height=max(420, 25 * len(frame) + 140), showlegend=False,
        xaxis={"title": axis, "rangemode": "tozero"},
        yaxis={"title": "Ticker", "autorange": "reversed", "categoryorder": "array", "categoryarray": frame.Ticker.tolist()},
        margin={"t": 75, "b": 65},
    )
    return figure


def rsi_figure(frame: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    figure = indicator_bar(frame, RSI, "RSI — highest first", "RSI (14-day index)", colors)
    figure.add_vline(x=30, line_dash="dash", line_color="gray", annotation_text="30 · oversold", annotation_position="top left")
    figure.add_vline(x=70, line_dash="dash", line_color="gray", annotation_text="70 · overbought", annotation_position="top right")
    figure.update_xaxes(range=[min(0, float(frame[RSI].min())), max(100, float(frame[RSI].max()))])
    return figure


def range_figure(frame: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    figure = indicator_bar(frame, "52W Position", "Position within the 52-week range — highest first", "52-week range position (%)", colors)
    figure.update_xaxes(
        ticksuffix="%",
        range=[min(0, float(frame["52W Position"].min())) - 3, max(100, float(frame["52W Position"].max())) + 3],
    )
    figure.add_vline(x=100, line_dash="dot", line_color="gray")
    return figure


def returns_figure(frame: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    figure = go.Figure()
    for column, pattern in zip(RETURN_COLUMNS, ("", "/", "x")):
        figure.add_trace(go.Bar(
            name=column, x=frame.Ticker.tolist(),
            y=[None if pd.isna(value) else float(value) for value in frame[column]],
            marker={"color": [ticker_color(t, colors) for t in frame.Ticker], "pattern": {"shape": pattern}},
            hovertemplate="%{x}<br>" + column + ": %{y:.2f}%<extra></extra>",
        ))
    figure.update_layout(
        title="Historical returns by ticker — ranked by five-year return", barmode="group", height=550,
        xaxis={"title": "Ticker", "categoryorder": "array", "categoryarray": frame.Ticker.tolist(), "tickangle": -45},
        yaxis={"title": "Return (%)", "ticksuffix": "%", "rangemode": "tozero"},
        legend={"title": "Return period (patterns distinguish horizons)", "orientation": "h"},
        margin={"b": 90, "t": 70},
    )
    return figure
