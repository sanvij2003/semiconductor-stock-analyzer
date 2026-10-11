# Semiconductor Stock Financial Analysis

This Streamlit app analyzes semiconductor stocks through company snapshots, peer comparisons, growth versus valuation, technical trends, and long-term returns.
The data comes from a Finviz Elite screener export.
The app was built with Replit Agent for Week 1 of the Mastering Agentic AI course.

## Open the app

Press **Run** to open the Streamlit app in the Replit preview.
The sidebar filters by market cap (in billions of dollars) and ticker.
The ticker filter starts empty, which includes all stocks; selections narrow the
results. Market cap range labels use compact $B/$T amounts while the underlying
filter still uses the same dollar values. The subtitle reads
"Data as of Oct 10, 2026, from a Finviz Elite screener export".
The five tabs share these filters:
- **Company Snapshot:** select a ticker to view all eleven KPI cards.
- **Peer Comparison:** sortable table of all matching stocks and four rankings:
  Forward P/E, P/S, Gross Margin and EPS Next Y.
- **Growth vs Valuation:** Plotly scatter with EPS Next Y on x, Forward P/E on y,
  market-cap bubbles, ticker labels and an unweighted OLS fitted line.
- **Technicals & Trend:** moving-average scatter, RSI rankings, and 52-week range
  positions.
- **Long-term Returns:** grouped Perf YTD, Perf 3Y, and Perf 5Y bars per ticker.

Use **Download filtered data** in the sidebar to save the matching stocks as CSV.
The download preserves dollar amounts, percentage-point values and blank missing
cells without display rounding; it is disabled when no stocks match.
Each ticker keeps the same chart color across rankings, the scatter and filter
changes. Chart captions explain how to read each view, and missing metrics include
helpful messages rather than being substituted with zero.
All tables show missing cells as `n/a`, with numeric sorting preserved.
The peer table shows important metrics first, displays market caps like the KPI
cards, and labels the RSI column as `RSI` without changing the CSV headers.
OLS formulas and technical details are in collapsed **How this is calculated**
sections.

### Technicals & Trend and Long-term Returns

These tabs follow Growth vs Valuation and use the same sidebar filters and ticker
colors without changing the existing tabs.

- Moving-average scatter: SMA200 on x and SMA50 on y, in percentage points, with
  zero reference lines, quadrant labels, and a compact trend-group table.
  Uptrend requires both values above zero, Downtrend both below zero, and Mixed
  includes opposite signs or exact-zero boundaries; missing inputs are reported.
- RSI: the `Relative Strength Index (14)` column, ranked high to low, with dashed
  oversold/overbought references at 30/70.
- 52-week position: `(Price - 52W Low) / (52W High - 52W Low) * 100`, ranked high
  to low; missing inputs, zero-width or reversed ranges are unavailable.
  Positions outside 0–100 are not clipped.
- Historical returns: grouped Perf YTD, Perf 3Y and Perf 5Y bars, sorted by Perf
  5Y descending with missing five-year values last; negative values remain
  signed, and missing values stay gaps rather than being converted to zero.
  Ticker hues remain consistent, while fill patterns distinguish time horizons.

The app caches `data/fundamentals.csv` and reloads it when the file changes.
It does not download data automatically. Missing KPI values appear as `n/a`.
Percentage-point values such as `74.67` display as `74.67%`.
The signed percentage from the 52-week high is `(Price / 52W High - 1) × 100`.

The growth scatter excludes only stocks missing EPS Next Y or Forward P/E after
numeric validation; it lists the tickers and reasons below the chart.
Negative growth and zero values are accepted. The axes automatically cover all
points, with no y-axis cap. Missing market caps use a minimum visible bubble size
instead of excluding an otherwise valid growth/valuation point.
Distance is actual Forward P/E minus fitted Forward P/E, in P/E multiple units:
positive means above the line (priced richly for expected growth).
Excluded stocks or unavailable fits show `n/a` in the distance table.
The fitted line needs two stocks with distinct growth values. It describes this
sample, not a forecast or an investment recommendation.

## Download the data

1. Store the Finviz Elite key in the Replit Secret `FINVIZ_API_KEY`.
2. Supply the exact screener export URL with `auth={FINVIZ_API_KEY}`.
   Keep its filters and selected columns intact. Never put the actual key in a
   command, source file, URL configuration, or chat.
3. Run:

   ```sh
   python3 fetch_data.py --url 'YOUR_FINVIZ_EXPORT_URL_WITH_auth={FINVIZ_API_KEY}'
   ```

   Alternatively, set the non-secret `FINVIZ_EXPORT_URL` to that URL template
   and run `python3 fetch_data.py`.

The command prints the first five cleaned rows and the complete column list.
`FINVIZ_EXPORT_URL` is configured for your supplied semiconductor screener:
the large-cap, USA, semiconductor filters and saved custom preset are retained.
The CSV endpoint is `export.ashx` with custom view `v=151`. Simply run
`python3 fetch_data.py` to refresh the data.

## Output and column meaning

- `data/raw_export.csv`: original downloaded bytes.
- `data/fundamentals.csv`: cleaned data with empty cells representing missing values.
- `Market Cap`: multiply the export's millions by 1,000,000 to get dollars.
- `Perf YTD`, `Perf 3Y`, `Perf 5Y`, `EPS This Y`, `EPS Next Y`, `Gross Margin`,
  `Insider Own`, `SMA50`, `SMA200`: numeric percentage points, unchanged in scale.
  The live export includes trailing `%` symbols; only those symbols are removed.
- `SMA50` and `SMA200`: percentage distance from the moving averages, not prices.
- `52W Range`: retained as text, with numeric `52W Low` and `52W High` added.
- `No.`: removed.
- Finviz's longer export headers are mapped to the assignment's names in the
  cleaned data only; the raw download is never rewritten.

Each HTTP request, including redirects, is spaced by at least 0.6 seconds,
keeping this project's requests below 10 per five seconds. Concurrent runs
share the limiter. Requests from other tools using the same account are outside
this project's control.

Invalid CSV, unexpected numeric formats, unsafe redirects, and missing required
columns stop processing explicitly. Network error output never includes the
authenticated URL or API key.

Dependencies are managed in `pyproject.toml` and `uv.lock`.
