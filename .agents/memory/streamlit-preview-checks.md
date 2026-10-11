---
name: Streamlit preview checks
description: Distinguish early Streamlit loading snapshots from genuinely broken previews.
---

A blank or skeleton-only preview snapshot does not establish that Streamlit is broken.

**Why:** The snapshot captured the initial loading state even though the proxied
health endpoint and WebSocket worked, and the actual page rendered the full app
after roughly two seconds in a browser.

**How to apply:** Before changing a healthy server based on a blank snapshot,
confirm that the browser receives the application heading and metrics after
initialization. Check the proxy health and WebSocket when routing is uncertain.

Use the full `https://` development URL when troubleshooting browser connection
resets, and check HTTP and HTTPS separately before restarting a healthy app.

**Why:** In this workspace, the development host refused HTTP connections while
HTTPS and the secure Streamlit WebSocket worked. A browser connection reset alone
does not establish that the application server needs a restart.

**How to apply:** Confirm the protocol the user is opening. If HTTPS is healthy,
ask them to use the complete HTTPS address; if it still fails, isolate browser or
network filtering rather than repeatedly changing application code.

A failed managed start reporting an occupied port can coexist with an older,
healthy Streamlit process.

**Why:** A subsequent managed start failed because an earlier app process still
held the assigned port, while the health endpoint continued to respond.

**How to apply:** Inspect the exact process command and health endpoint before
restarting. If an older duplicate is confirmed, terminate only that app process
gracefully and restart the existing managed workflow; do not change ports or add
a replacement workflow.
