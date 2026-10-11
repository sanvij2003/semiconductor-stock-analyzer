"""Lightweight local checks; no browser or external API calls."""

import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import app


class FormattingTests(unittest.TestCase):
    def test_missing_values(self):
        for value in (None, pd.NA, float("nan"), float("inf"), "", "invalid"):
            self.assertEqual(app.format_number(value), "n/a")
            self.assertEqual(app.format_market_cap(value), "n/a")
            self.assertEqual(app.format_high_distance(value, 100), "n/a")
        self.assertEqual(app.format_high_distance(10, 0), "n/a")
        self.assertEqual(app.format_high_distance(10, -1), "n/a")

    def test_units_and_sign(self):
        self.assertEqual(app.format_market_cap(196825650000), "$196.83B")
        self.assertEqual(app.format_market_cap(5525647970000), "$5.53T")
        self.assertEqual(app.format_number(74.67, suffix="%"), "74.67%")
        self.assertEqual(app.format_high_distance(90, 100), "-10.00%")
        self.assertEqual(app.format_high_distance(100, 100), "+0.00%")
        self.assertEqual(app.format_high_distance(110, 100), "+10.00%")

    def test_inclusive_filters(self):
        frame = pd.DataFrame({"Ticker": ["A", "B", "C"], "Market Cap": [1e9, 2e9, 3e9]})
        self.assertEqual(app.filter_companies(frame, (1, 2), ["A", "B", "C"])["Ticker"].tolist(), ["A", "B"])
        self.assertTrue(app.filter_companies(frame, (1, 3), []).empty)
        self.assertEqual(frame["Market Cap"].tolist(), [1e9, 2e9, 3e9])

    def test_cache_and_file_refresh(self):
        app.load_fundamentals.clear()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fundamentals.csv"
            path.write_text("Ticker,Price\nA,1\n")
            signature = path.stat()
            read = pd.read_csv
            with patch.object(app.pd, "read_csv", wraps=read) as reader:
                first = app.load_fundamentals(str(path), signature.st_mtime_ns, signature.st_size)
                second = app.load_fundamentals(str(path), signature.st_mtime_ns, signature.st_size)
                self.assertEqual(reader.call_count, 1)
                self.assertEqual(first.iloc[0]["Price"], second.iloc[0]["Price"])
                path.write_text("Ticker,Price\nA,222\n")
                new_signature = path.stat()
                updated = app.load_fundamentals(str(path), new_signature.st_mtime_ns, new_signature.st_size)
                self.assertEqual(reader.call_count, 2)
                self.assertEqual(updated.iloc[0]["Price"], 222)
                self.assertTrue(math.isnan(updated.iloc[0]["P/E"]))


class WidgetTests(unittest.TestCase):
    def test_snapshot_filters_and_missing_kpis(self):
        at = AppTest.from_file(str(Path(app.__file__))).run()
        self.assertFalse(at.exception)
        self.assertEqual([tab.label for tab in at.tabs][:3], ["Company Snapshot", "Peer Comparison", "Growth vs Valuation"])
        self.assertEqual(len(at.metric), 11)
        self.assertEqual(at.multiselect[0].value, [])
        at.selectbox[0].select("NVDA").run()
        values = {metric.label: metric.value for metric in at.metric}
        self.assertEqual(values["Gross Margin"], "74.67%")
        self.assertEqual(values["Market Cap"], "$5.53T")
        self.assertEqual(values["RSI"], "52.96")
        self.assertEqual(values["% from 52-week high"], "-5.79%")
        at.selectbox[0].select("CBRS").run()
        values = {metric.label: metric.value for metric in at.metric}
        self.assertEqual(values["P/E"], "n/a")
        self.assertEqual(values["EPS This Y"], "n/a")
        at.multiselect[0].set_value([]).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.metric), 11)
        self.assertEqual(len(at.dataframe[0].value), 22)
        at.multiselect[0].set_value(["ADI", "NVDA"]).run()
        self.assertEqual(at.selectbox[0].options, ["ADI", "NVDA"])
        at.selectbox[0].select("NVDA").run()
        at.slider[0].set_value((10.07, 200.0)).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.selectbox[0].value, "ADI")

    def test_singleton_and_missing_file(self):
        self.addCleanup(setattr, app, "DATA_PATH", app.DATA_PATH)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fundamentals.csv"
            path.write_text("Ticker,Market Cap,Price\nONLY,1000000000,10\n")
            code = f"import app\nfrom pathlib import Path\napp.DATA_PATH = Path({str(path)!r})\napp.main()"
            at = AppTest.from_string(code).run()
            self.assertFalse(at.exception)
            self.assertEqual(at.selectbox[0].value, "ONLY")
            self.assertEqual(len(at.metric), 11)
            self.assertEqual({m.label: m.value for m in at.metric}["RSI"], "n/a")
            path.unlink()
            at.run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.error), 1)


if __name__ == "__main__":
    unittest.main()
