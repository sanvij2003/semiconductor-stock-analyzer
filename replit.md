# Semiconductor Stock Financial Analysis

Week 1 financial analysis assignment, built incrementally from the user's step-by-step prompts.

## Assignment scope

- Follow the user's prompts one step at a time; do not add work beyond the requested step.
- Prompts 1–3 supply the data layer, shared sidebar filters, Company Snapshot, Peer Comparison and Growth vs Valuation. Do not add other tabs.
- Prompt 5 is display-only polish: consistent ticker colors, chart labels/captions, filtered CSV download and helpful missing/empty messages; do not change calculations.
- The later Growth vs Valuation correction keeps negative growth, excludes only missing EPS Next Y or Forward P/E, lists excluded tickers, and removes the y-axis cap.
- The intended dashboard framework is Streamlit, not React.
- Keep the Finviz key in `FINVIZ_API_KEY` via `os.environ`; never print it.
- Run `python3 fetch_data.py --url 'URL_WITH_auth={FINVIZ_API_KEY}'`.
- See `README.md` for input configuration and the data-unit rules.
- The Node services below are the original template, not the assignment app.

## Run & Operate

- The Run button launches the Streamlit Company Snapshot preview.
- `artifacts/company-snapshot` registers the preview route; the actual Python app stays in root `app.py`.
- Its managed workflow supplies the Streamlit port via `PORT`; do not add a duplicate standalone workflow.
- `python3 -m unittest discover -s tests` — local snapshot and widget checks

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

_Populate as you build — short repo map plus pointers to the source-of-truth file for DB schema, API contracts, theme files, etc._

## Architecture decisions

_Populate as you build — non-obvious choices a reader couldn't infer from the code (3-5 bullets)._

## Product

_Describe the high-level user-facing capabilities of this app once they exist._

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
