---
name: Finviz export behavior
description: Non-obvious upstream behavior discovered while connecting the Week 1 assignment to Finviz Elite.
---

Finviz's overview export view can ignore a saved preset's custom column selection.
Use the custom view for the assignment's saved preset, while keeping its stock filters intact.

**Why:** The user supplied a screener link using the overview view; its CSV contained only basic fields even though the saved custom preset included the assignment's financial fields.

**How to apply:** When changing screener/export configuration, verify the actual returned column set rather than assuming a preset parameter alone selects its custom fields.

The live export's percentage formatting can differ from the assignment wording. Preserve percentage-point magnitudes; do not infer fractional units from a trailing `%` display symbol.

**Why:** The assignment described plain percentage-point numbers, but the live CSV returned percentage-point numbers with `%` suffixes.

**How to apply:** Verify the actual payload before altering units, and preserve the original download for comparison.
