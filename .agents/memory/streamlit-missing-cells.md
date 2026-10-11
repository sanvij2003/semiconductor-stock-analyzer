---
name: Streamlit missing-cell display
description: Preserve numeric sorting while changing how Streamlit displays missing table cells.
---

Pandas Styler's missing-value formatting does not override Streamlit's native
missing-cell renderer. Use the dataframe's native placeholder instead of
replacing numeric missing values with strings.

**Why:** Streamlit displayed `None` for null numeric cells even though the
serialized Styler display values already contained `n/a`. String replacements
would change numeric column types and risk changing table sorting.

**How to apply:** When customizing missing-cell text, keep the underlying
dataframe numeric and set its display placeholder. Check the table configuration
as well as the serialized Styler values; formatting alone is not sufficient.
