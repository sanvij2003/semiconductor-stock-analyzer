---
name: Workspace publish security checks
description: Why unrelated Node dependencies can block publishing the Python dashboard.
---

Publishing security checks can cover dependencies across the workspace, not just
the Python dashboard's imports.

**Why:** A vulnerable transitive dependency in the scaffolded API server blocked
publishing even though the Streamlit application did not depend on that API.

**How to apply:** Start with the recorded publish failure and inspect the complete
workspace dependency tree when it names a Node package. Prefer a compatible
update to its direct parent dependency, retain package-firewall protections, and
verify the production dependency audit and affected service build. Do not change
dashboard calculations or remove unrelated services to work around a security
gate.
