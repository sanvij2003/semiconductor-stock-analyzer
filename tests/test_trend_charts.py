"""New indicators, gap semantics, tab order and shared-filter regressions."""

import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import app
from chart_presentation import build_ticker_colors
from technical_tabs import CAPTIONS
from trend_charts import (
    RSI, range_data, range_figure, returns_data, returns_figure,
    rsi_data, rsi_figure, trend_data, trend_figure,
)


class TechnicalTests(unittest.TestCase):
    def test_quadrants_boundaries_missing_and_original_percentage_units(self):
        frame = pd.DataFrame({
            "Ticker": ["UP", "DOWN", "LEFT", "RIGHT", "ZERO", "MISSING"],
            "SMA200": [12, -4, -1, 5, 0, None],
            "SMA50": [74.67, -8, 7, -2, 0, 8],
        })
        original = frame.copy(deep=True)
        points, groups, missing = trend_data(frame)
        self.assertEqual(points.Group.tolist(), ["Uptrend", "Downtrend", "Mixed", "Mixed", "Mixed"])
        self.assertEqual(missing, ["MISSING"])
        self.assertEqual(groups.set_index("Group").loc["Mixed", "Tickers"], "LEFT, RIGHT, ZERO")
        figure = trend_figure(points, build_ticker_colors(frame.Ticker))
        self.assertEqual(figure.data[0].y[0], 74.67)
        self.assertEqual(len(figure.layout.shapes), 2)
        self.assertEqual([a.text for a in figure.layout.annotations], ["Uptrend", "Downtrend", "Mixed", "Mixed"])
        self.assertLess(figure.layout.xaxis.range[0], min(points.SMA200))
        self.assertGreater(figure.layout.yaxis.range[1], max(points.SMA50))
        pd.testing.assert_frame_equal(original, frame)

    def test_rsi_sort_thresholds_and_colors(self):
        frame = pd.DataFrame({"Ticker": ["B", "A", "C", "NA"], RSI: [30, 70, 90, None]})
        colors = build_ticker_colors(frame.Ticker)
        ranked = rsi_data(frame)
        self.assertEqual(ranked.Ticker.tolist(), ["C", "A", "B"])
        figure = rsi_figure(ranked, colors)
        self.assertEqual(list(figure.data[0].x), [90, 70, 30])
        self.assertEqual([line.x0 for line in figure.layout.shapes], [30, 70])
        self.assertTrue(all(line.line.dash == "dash" for line in figure.layout.shapes))
        self.assertEqual(list(figure.data[0].marker.color), [colors[t] for t in ranked.Ticker])

    def test_range_positions_do_not_clamp_and_invalid_ranges_are_missing(self):
        frame = pd.DataFrame({
            "Ticker": ["LOW", "MID", "HIGH", "BEYOND", "ZERO", "REVERSED", "NA"],
            "Price": [10, 15, 20, 25, 10, 10, None],
            "52W Low": [10, 10, 10, 10, 10, 20, 10],
            "52W High": [20, 20, 20, 20, 10, 10, 20],
        })
        ranked = range_data(frame)
        self.assertEqual(ranked.Ticker.tolist(), ["BEYOND", "HIGH", "MID", "LOW"])
        self.assertEqual(ranked["52W Position"].tolist(), [150, 100, 50, 0])
        figure = range_figure(ranked, build_ticker_colors(frame.Ticker))
        self.assertGreater(figure.layout.xaxis.range[1], 150)

    def test_returns_missing_are_null_gaps_and_negative_values_stay(self):
        frame = pd.DataFrame({
            "Ticker": ["A", "B", "C", "D"],
            "Perf YTD": [None, -10, 0, None],
            "Perf 3Y": [12, None, -20, None],
            "Perf 5Y": [100, 200, None, None],
        })
        original = frame.copy(deep=True)
        ranked = returns_data(frame)
        self.assertEqual(ranked.Ticker.tolist(), ["B", "A", "C", "D"])
        colors = build_ticker_colors(frame.Ticker)
        figure = returns_figure(ranked, colors)
        self.assertEqual(list(figure.data[0].y), [-10, None, 0, None])
        self.assertEqual(list(figure.data[1].y), [None, 12, -20, None])
        self.assertEqual(list(figure.data[2].y), [200, 100, None, None])
        self.assertEqual(figure.layout.barmode, "group")
        self.assertEqual([trace.marker.pattern.shape for trace in figure.data], ["", "/", "x"])
        self.assertTrue(all(list(trace.marker.color) == [colors[t] for t in ranked.Ticker] for trace in figure.data))
        pd.testing.assert_frame_equal(original, frame)

    def test_tabs_share_filters_and_each_new_chart_has_a_caption(self):
        at = AppTest.from_file(str(Path(app.__file__)), default_timeout=10).run()
        self.assertFalse(at.exception)
        self.assertEqual([tab.label for tab in at.tabs], [
            "Company Snapshot", "Peer Comparison", "Growth vs Valuation",
            "Technicals & Trend", "Long-term Returns",
        ])
        self.assertEqual(len(at.tabs[3].get("plotly_chart")), 3)
        self.assertEqual(len(at.tabs[4].get("plotly_chart")), 1)
        for caption in CAPTIONS:
            self.assertIn(caption, [text.value for text in at.caption])
        at.multiselect[0].set_value(["NVDA"]).run()
        self.assertFalse(at.exception)
        group_table = at.tabs[3].dataframe[0]
        self.assertEqual(group_table.proto.placeholder, "n/a")
        self.assertEqual(group_table.value.loc[group_table.value.Group.eq("Uptrend"), "Tickers"].iloc[0], "NVDA")
        self.assertEqual(len(at.tabs[3].get("plotly_chart")), 3)
        self.assertEqual(len(at.tabs[4].get("plotly_chart")), 1)

    def test_new_tabs_handle_all_missing_columns_without_crashing(self):
        code = (
            "import pandas as pd\nfrom technical_tabs import render_technicals,render_returns\n"
            "frame=pd.DataFrame({'Ticker':['ONLY']})\n"
            "render_technicals(frame,{})\nrender_returns(frame,{})\n"
        )
        at = AppTest.from_string(code, default_timeout=10).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("plotly_chart")), 0)
        self.assertEqual(len(at.info), 4)


if __name__ == "__main__":
    unittest.main()
