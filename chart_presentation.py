"""Display-only chart labels, explanations and shared ticker colors."""

from collections.abc import Iterable
import hashlib
import math

from plotly.colors import qualitative


RANKING_TITLES = {
    "Forward P/E": "Forward P/E ranking — lowest first",
    "P/S": "Price-to-sales ranking — lowest first",
    "Gross Margin": "Gross margin ranking — highest first",
    "EPS Next Y": "Expected EPS growth next year — highest first",
}
AXIS_LABELS = {
    "Forward P/E": "Forward price-to-earnings ratio (×)",
    "P/S": "Price-to-sales ratio (×)",
    "Gross Margin": "Gross margin (%)",
    "EPS Next Y": "Expected EPS growth next year (%)",
}
RANKING_CAPTIONS = {
    "Forward P/E": "Shorter bars indicate lower forward price-to-earnings multiples, ranked lowest first.",
    "P/S": "Shorter bars indicate lower price-to-sales multiples, ranked lowest first.",
    "Gross Margin": "Longer bars show more gross profit per dollar of revenue, with the highest margins first.",
    "EPS Next Y": "Longer positive bars indicate higher expected EPS growth, while negative bars indicate an expected decline.",
}
GROWTH_CAPTION = (
    "Each labeled bubble plots expected EPS growth (%) against Forward P/E (×), "
    "its area represents market cap (USD), and points above the fitted line have "
    "higher valuations than the growth trend implies."
)
EMPTY_FILTER_MESSAGE = (
    "No companies match your filters yet — widen the market cap range or clear "
    "the ticker filter in the sidebar to bring companies back."
)


def format_market_cap_label(value: object) -> str:
    """Display-only dollar abbreviation matching the existing KPI cards."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "n/a"
    if not math.isfinite(number) or number < 0:
        return "n/a"
    scale, suffix = (1e12, "T") if number >= 1e12 else (1e9, "B")
    return f"${number / scale:,.2f}{suffix}"


def ticker_color(ticker: str, colors: dict[str, str] | None = None) -> str:
    """Explicit map first; a deterministic fallback never depends on sort order."""
    if colors is not None and ticker in colors:
        return colors[ticker]
    digest = hashlib.sha256(str(ticker).encode("utf-8")).digest()
    hue = int.from_bytes(digest[:4], "big") / (2**32) * 360
    return f"hsl({hue:.4f}, 65%, 42%)"


def build_ticker_colors(tickers: Iterable[str]) -> dict[str, str]:
    """Build once from the full dataset, before any sidebar or metric filtering."""
    universe = sorted(set(tickers))
    return {
        ticker: qualitative.Alphabet[index] if index < len(qualitative.Alphabet) else ticker_color(ticker)
        for index, ticker in enumerate(universe)
    }
