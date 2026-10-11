"""Regression, exclusion and chart checks without downloads or a browser."""

import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

import app
from peer_analysis import analyze_growth, growth_figure, ranked_peers, ranking_figure


def sample(xs=(0, 10, 20), ys=(5, 25, 45)):
    return pd.DataFrame({
        "Ticker": [f"S{i}" for i in range(len(xs))],
        "EPS Next Y": xs, "Forward P/E": ys, "Market Cap": [1e9] * len(xs),
    })


class AnalysisTests(unittest.TestCase):
    def test_known_line_and_uncapped_axis(self):
        source = sample()
        original = source.copy(deep=True)
        result = analyze_growth(source)
        self.assertAlmostEqual(result.slope, 2)
        self.assertAlmostEqual(result.intercept, 5)
        self.assertEqual(result.distances["Trend-implied Forward P/E"].tolist(), [5, 25, 45])
        self.assertEqual(result.distances["Distance (P/E multiple)"].tolist(), [0, 0, 0])
        self.assertEqual(result.distances["Interpretation"].tolist(), ["On trend"] * 3)
        figure = growth_figure(result)
        self.assertIsNone(figure.layout.yaxis.range)
        self.assertTrue(figure.layout.yaxis.autorange)
        self.assertFalse(figure.data[0].cliponaxis)
        self.assertEqual(list(figure.data[0].y), [5, 25, 45])
        self.assertEqual(list(figure.data[1].y), [5, 45])
        self.assertEqual(list(figure.data[0].text), ["S0", "S1", "S2"])
        self.assertEqual(figure.data[0].marker.sizemode, "area")
        pd.testing.assert_frame_equal(source, original)

    def test_above_and_below_signs(self):
        result = analyze_growth(sample(ys=(5, 30, 45)))
        values = result.distances.set_index("Ticker")
        self.assertGreater(values.loc["S1", "Distance (P/E multiple)"], 0)
        self.assertIn("priced richly", values.loc["S1", "Interpretation"])
        self.assertLess(values.loc["S0", "Distance (P/E multiple)"], 0)
        self.assertIn("Below", values.loc["S0", "Interpretation"])
        self.assertAlmostEqual(result.distances["Distance (P/E multiple)"].sum(), 0)

    def test_exclusions_only_use_required_metrics(self):
        source = sample(xs=(0, -1, None, 10, 20, 30, 40, 50), ys=(0, 10, 20, -1, float("inf"), 30, 40, 50))
        source["Market Cap"] = [0, 1e9, 1e9, 1e9, 1e9, -1, None, 1e9]
        source["Gross Margin"] = float("nan")
        result = analyze_growth(source)
        self.assertEqual(result.eligible["Ticker"].tolist(), ["S0", "S1", "S3", "S5", "S6", "S7"])
        self.assertEqual(result.excluded["Ticker"].tolist(), ["S2", "S4"])
        self.assertIn("EPS Next Y: missing", result.excluded.iloc[0]["Reason"])
        figure = growth_figure(result)
        self.assertEqual(len(figure.data[0].x), 6)
        self.assertTrue(all(value >= 0 for value in figure.data[0].marker.size))
        self.assertEqual(len(result.distances), 8)
        excluded = result.distances.loc[result.distances["Ticker"].isin(result.excluded["Ticker"])]
        self.assertTrue(excluded["Distance (P/E multiple)"].isna().all())

    def test_degenerate_inputs(self):
        for source in (sample(xs=(), ys=()), sample(xs=(10,), ys=(20,)), sample(xs=(10, 10), ys=(20, 30))):
            result = analyze_growth(source)
            self.assertIsNone(result.slope)
            self.assertTrue(result.fit_message)
            self.assertTrue(result.distances["Distance (P/E multiple)"].isna().all())
        result = analyze_growth(sample(ys=(0, 0, 0)))
        self.assertTrue(growth_figure(result).layout.yaxis.autorange)
        self.assertIsNone(growth_figure(result).layout.yaxis.range)
        self.assertEqual(result.slope, 0)

    def test_ranking_missing_and_negative_growth(self):
        source = sample(xs=(74.67, -3.92, None))
        ranked = ranked_peers(source, "EPS Next Y", False)
        self.assertEqual(ranked["EPS Next Y"].tolist(), [74.67, -3.92])
        figure = ranking_figure(ranked, "EPS Next Y")
        self.assertEqual(list(figure.data[0].x), [74.67, -3.92])
        self.assertEqual(figure.layout.xaxis.ticksuffix, "%")
        self.assertEqual(figure.layout.yaxis.autorange, "reversed")
        self.assertEqual(ranked_peers(source, "Forward P/E", True)["Ticker"].tolist(), ["S0", "S1", "S2"])
        self.assertTrue(ranked_peers(source, "Absent", True).empty)

    def test_saved_data_exclusions(self):
        source = pd.read_csv(app.DATA_PATH)
        result = analyze_growth(source)
        self.assertEqual(result.excluded["Ticker"].tolist(), ["CBRS"])
        self.assertEqual(len(result.eligible), 21)
        for ticker in ["ALAB", "INTC", "QCOM", "SWKS"]:
            self.assertIn(ticker, result.eligible["Ticker"].tolist())
        self.assertTrue(result.eligible.loc[result.eligible["Ticker"].isin(["QCOM", "SWKS"]), "EPS Next Y"].lt(0).all())
        self.assertEqual(len(result.distances), 22)


class SharedFilterTests(unittest.TestCase):
    def test_all_tabs_share_filters(self):
        at = AppTest.from_file(str(app.DATA_PATH.parent.parent / "app.py"), default_timeout=10).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("plotly_chart")), 9)
        self.assertEqual(len(at.dataframe[0].value), 22)
        self.assertEqual(at.dataframe[1].value["Ticker"].tolist(), ["CBRS"])
        at.multiselect[0].set_value(["ADI", "NVDA", "CBRS"]).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.dataframe[0].value["Ticker"].tolist(), ["ADI", "CBRS", "NVDA"])
        self.assertEqual(at.dataframe[1].value["Ticker"].tolist(), ["CBRS"])
        self.assertEqual(at.dataframe[2].value["Ticker"].tolist(), ["ADI", "CBRS", "NVDA"])
        at.slider[0].set_value((10.07, 200.0)).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.dataframe[0].value["Ticker"].tolist(), ["ADI", "CBRS"])
        at.multiselect[0].set_value([]).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.tabs), 5)
        self.assertGreater(len(at.dataframe[0].value), 0)
        at.multiselect[0].set_value(["CBRS"]).run()
        at.slider[0].set_value((10.07, 10.08)).run()
        self.assertEqual(len(at.info), 5)
        self.assertEqual(len(at.get("plotly_chart")), 0)

    def test_all_missing_and_singleton_render(self):
        code = (
            "import pandas as pd\n"
            "from analysis_tabs import render_peers, render_growth\n"
            "frame=pd.DataFrame({'Ticker':['ONLY'], 'Market Cap':[0], 'EPS Next Y':[0], 'Forward P/E':[0]})\n"
            "render_peers(frame)\nrender_growth(frame)\n"
        )
        at = AppTest.from_string(code, default_timeout=10).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("plotly_chart")), 3)
        self.assertEqual(len(at.warning), 1)
        at = AppTest.from_string(code.replace("'EPS Next Y':[0]", "'EPS Next Y':[None]")).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.dataframe[1].value["Ticker"].tolist(), ["ONLY"])
        self.assertTrue(at.dataframe[2].value["Distance (P/E multiple)"].isna().all())


if __name__ == "__main__":
    unittest.main()
