---
name: Read-only Git checks
description: Avoid index-refresh writes when inspecting changes in this workspace.
---

Some apparently read-only Git diff commands can attempt to acquire an index lock
and be rejected by the workspace's Git protection.

**Why:** Diff checks triggered an index-lock write even with optional locks
disabled, while retrieving committed file contents with `git show HEAD:path`
worked.

**How to apply:** For verification that does not require updating Git state,
compare committed file contents with working files directly. Do not bypass Git
protections or repeatedly retry the same diff command for a read-only check.

For requests to keep calculations unchanged, capture the current working-file
baseline before editing rather than treating `HEAD` as the previous turn.

**Why:** `HEAD` can lag already implemented standalone changes, so comparing
against it can incorrectly attribute an earlier request's edits to the current
request.

**How to apply:** Use a temporary pre-edit baseline or targeted regression checks
for the current request. A committed-file comparison is useful only when that
commit is known to represent the actual starting state.
