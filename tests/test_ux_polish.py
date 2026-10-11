"""Display-only polish and lossless filtered-download regression checks."""

from io import BytesIO
from pathlib import Path
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

import app
from chart_presentation import (
    AXIS_LABELS, GROWTH_CAPTION, RANKING_CAPTIONS, build_ticker_colors, ticker_color,
    format_market_cap_label,
)
from streamlit.dataframe_util import convert_arrow_bytes_to_pandas_df
from peer_analysis import RANKINGS, analyze_growth, growth_figure, ranked_peers, ranking_figure


class PresentationTests(unittest.TestCase):
    def test_colors_follow_tickers_not_ranking_or_filters(self):
        frame = pd.read_csv(app.DATA_PATH)
        colors = build_ticker_colors(frame["Ticker"])
        self.assertEqual(len(set(colors.values())), len(frame))
        self.assertEqual(colors, build_ticker_colors(reversed(frame["Ticker"].tolist())))
        result = analyze_growth(frame)
        bubble = growth_figure(result, colors).data[0]
        scatter_colors = dict(zip(bubble.text, bubble.marker.color))
        for metric, ascending in RANKINGS:
            full = ranking_figure(ranked_peers(frame, metric, ascending), metric, colors)
            bars = dict(zip(full.data[0].y, full.data[0].marker.color))
            for ticker in set(bars) & set(scatter_colors):
                self.assertEqual(bars[ticker], scatter_colors[ticker])
            subset = frame.loc[frame["Ticker"].isin(["ADI", "NVDA", "CBRS"])]
            filtered = ranking_figure(ranked_peers(subset, metric, ascending), metric, colors)
            for ticker, color in zip(filtered.data[0].y, filtered.data[0].marker.color):
                self.assertEqual(color, bars[ticker])
            self.assertEqual(full.layout.xaxis.title.text, AXIS_LABELS[metric])
        self.assertEqual(ticker_color("NEW"), ticker_color("NEW", colors))

    def test_figures_keep_values_and_fit_unchanged(self):
        frame = pd.read_csv(app.DATA_PATH)
        result = analyze_growth(frame)
        original = result.distances.copy(deep=True)
        colors = build_ticker_colors(frame["Ticker"])
        plain, colored = growth_figure(result), growth_figure(result, colors)
        self.assertEqual(plain.data[0].x, colored.data[0].x)
        self.assertEqual(plain.data[0].y, colored.data[0].y)
        self.assertEqual(plain.data[0].marker.size, colored.data[0].marker.size)
        self.assertEqual(plain.data[0].marker.sizeref, colored.data[0].marker.sizeref)
        self.assertEqual(plain.data[1].y, colored.data[1].y)
        self.assertEqual(plain.layout.yaxis.range, colored.layout.yaxis.range)
        pd.testing.assert_frame_equal(original, result.distances)

    def test_download_preserves_values_missing_cells_and_filters(self):
        frame = pd.read_csv(app.DATA_PATH)
        original = frame.copy(deep=True)
        filtered = app.filter_companies(frame, (0, 6000), ["CBRS", "NVDA"])
        contents = app.filtered_csv(filtered)
        downloaded = pd.read_csv(BytesIO(contents))
        self.assertEqual(downloaded["Ticker"].tolist(), ["CBRS", "NVDA"])
        nvda = downloaded.loc[downloaded["Ticker"].eq("NVDA")].iloc[0]
        self.assertEqual(nvda["Market Cap"], 5525647970000)
        self.assertEqual(nvda["Gross Margin"], 74.67)
        self.assertTrue(pd.isna(downloaded.loc[downloaded["Ticker"].eq("CBRS"), "Forward P/E"].iloc[0]))
        self.assertNotIn("Unnamed: 0", downloaded)
        pd.testing.assert_frame_equal(downloaded, filtered.reset_index(drop=True))
        pd.testing.assert_frame_equal(frame, original)

    def test_download_and_friendly_states_are_visible(self):
        at = AppTest.from_file(str(Path(app.__file__)), default_timeout=10).run()
        self.assertFalse(at.exception)
        button = at.get("download_button")[0]
        self.assertEqual(at.dataframe[0].proto.placeholder, "n/a")
        self.assertTrue(pd.api.types.is_numeric_dtype(at.dataframe[0].value["Forward P/E"]))
        self.assertEqual(button.proto.label, "Download filtered data")
        self.assertFalse(button.proto.disabled)
        captions = [caption.value for caption in at.caption]
        for expected in [*RANKING_CAPTIONS.values(), GROWTH_CAPTION]:
            self.assertIn(expected, captions)
        at.selectbox[0].select("CBRS").run()
        self.assertTrue(any("CBRS doesn't have usable values" in message.value for message in at.info))
        at.multiselect[0].set_value(["CBRS"]).run()
        self.assertFalse(at.exception)
        self.assertTrue(any("don't have Forward P/E values" in message.value for message in at.info))
        self.assertTrue(any("can't draw this comparison" in message.value for message in at.info))
        at.multiselect[0].set_value([]).run()
        self.assertFalse(at.exception)
        self.assertFalse(at.get("download_button")[0].proto.disabled)
        self.assertEqual(len(at.dataframe[0].value), 22)
        at.multiselect[0].set_value(["CBRS"]).run()
        at.slider[0].set_value((10.07, 10.08)).run()
        self.assertTrue(at.get("download_button")[0].proto.disabled)
        self.assertEqual(len(at.info), 5)
        self.assertTrue(all("widen the market cap range" in message.value for message in at.info))

    def test_compact_caps_match_kpis_and_table_stays_numeric(self):
        for value in [None, pd.NA, float("nan"), float("inf"), -1, 0, 196825650000, 5525647970000]:
            self.assertEqual(format_market_cap_label(value), app.format_market_cap(value))
        at = AppTest.from_file(str(Path(app.__file__)), default_timeout=10).run()
        peer = at.dataframe[0]
        self.assertEqual(
            peer.value.columns[:7].tolist(),
            ["Ticker", "Market Cap", "Price", "Forward P/E", "P/S", "EPS Next Y", "Gross Margin"],
        )
        self.assertIn("RSI", peer.value)
        self.assertNotIn("Relative Strength Index (14)", peer.value)
        self.assertTrue(pd.api.types.is_numeric_dtype(peer.value["Market Cap"]))
        formatted = convert_arrow_bytes_to_pandas_df(peer.proto.arrow_data.styler.display_values)
        self.assertEqual(formatted.loc[formatted.Ticker.eq("NVDA"), "Market Cap"].iloc[0], "$5.53T")
        self.assertEqual(formatted.loc[formatted.Ticker.eq("ADI"), "Market Cap"].iloc[0], "$196.83B")
        for table in at.dataframe:
            self.assertEqual(table.proto.placeholder, "n/a")
        captions = [caption.value for caption in at.caption]
        self.assertIn("Data as of Oct 10, 2026, from a Finviz Elite screener export", captions)
        self.assertIn("To $5.53T", captions)
        self.assertIn("From $10.07B", captions)
        self.assertEqual(at.multiselect[0].value, [])
        self.assertEqual(at.multiselect[0].proto.placeholder, "All tickers")
        self.assertEqual(at.slider[0].value, (10.07, 5525.65))
        self.assertEqual(len(at.expander), 2)
        for panel in at.expander:
            self.assertEqual(panel.label, "How this is calculated")
            self.assertFalse(panel.proto.expanded)
        growth_notes = at.expander[1]
        self.assertTrue(any("Unweighted OLS fit" in text.value for text in growth_notes.caption))


if __name__ == "__main__":
    unittest.main()
