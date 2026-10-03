# artful.exports

Storyboard exporters: Markdown ↔ HTML ↔ Storyboard.

Three forms supported today:

- [`to_markdown()`](#artful.exports.to_markdown) / [`from_markdown()`](#artful.exports.from_markdown) — round-trippable plain text
  for editor-friendly hand authoring + LLM consumption. Markdown is the
  canonical “give an LLM a storyboard to read or write” format.
- [`to_html()`](#artful.exports.to_html) — a self-contained HTML contact sheet for review in a
  browser; embeds <img> tags pointing at the panels’ urls / paths.

PDF export is deferred (needs reportlab; lives behind the `[pdf]` extra).

Each panel renders the same fields: panel id, time interval, framing, camera,
caption, image refs, notes. Round-trip-safe means: `from_markdown(to_markdown(s))`
preserves every field.

### Functions

| [`from_markdown`](#artful.exports.from_markdown)(text)                        | Parse [`to_markdown()`](#artful.exports.to_markdown)'s output back into a Storyboard + intervals.   |
|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| [`to_html`](#artful.exports.to_html)(storyboard[, panel_intervals])     | Render a self-contained HTML contact sheet.                                                                         |
| [`to_markdown`](#artful.exports.to_markdown)(storyboard[, panel_intervals]) | Render `storyboard` as Markdown.                                                                                    |

### artful.exports.from_markdown(text)

Parse [`to_markdown()`](#artful.exports.to_markdown)’s output back into a Storyboard + intervals.

Lines that don’t match a known shape are appended to the current panel’s
caption. Panels without an interval in the heading are returned with
no entry in the intervals dict (caller can pin them later).

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Storyboard`](artful.schema.html.md#artful.schema.Storyboard), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TimeInterval`]]

### artful.exports.to_html(storyboard, panel_intervals=None)

Render a self-contained HTML contact sheet.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.exports.to_markdown(storyboard, panel_intervals=None)

Render `storyboard` as Markdown.

If `panel_intervals` is given, each panel’s heading includes its
`[start..end]s` interval. If not, only ids are shown — useful when
the intervals haven’t been pinned yet.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
