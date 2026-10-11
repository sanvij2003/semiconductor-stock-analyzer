# Streamlit preview service

This package registers the root Python `app.py` with Replit's path-based preview.
It contains no React frontend. Its managed workflow supplies `PORT` and
`BASE_PATH`, then the package command starts Streamlit from the project root.

Keep application logic in `app.py` and dependencies in `pyproject.toml`.
