---
name: artful-markdown
description: >
  Round-trip storyboards through Markdown — artful's canonical "give an LLM
  a storyboard to read or write" format. Use this skill whenever an LLM
  needs to author, edit, or review storyboard panels as plain text, when
  the user wants to hand-edit a storyboard in a text editor, or when piping
  storyboard data through a chat / prompt context. Triggers on "storyboard
  markdown", "edit storyboard as text", "LLM storyboard", "from_markdown",
  "to_markdown", "panel as markdown", "round-trip storyboard", and on tasks
  that involve serializing or parsing storyboards as readable text. For
  building, persisting, and loading storyboards in code, see the `artful`
  skill.
---

# artful — Storyboards as Markdown

Markdown is artful's canonical format for LLM-driven authoring. The shape
is hand-editable, diff-friendly, and **round-trip lossless**:
`from_markdown(to_markdown(sb, intervals))` returns the same storyboard +
intervals.

```python
from artful import to_markdown, from_markdown
```

## The Markdown shape

```markdown
# The Bells — v1

- asset_id: `song-asset-id-abc`
- style: noir, candlelight
- aspect: 16:9

## panel p1 [0.00..4.00]s

- shot: `s01`
- framing: medium
- camera: static
- transition: fade

Thor at the piano

![seed](composite.png)
![thumb](https://x/thumb.png)

> notes: keep candle flicker subtle
```

Rules at a glance:

- The first `#` line is the storyboard title.
- Top-level `- key: value` lines (before the first panel) set
  `asset_id`, `style`, `aspect`. Backticks around `asset_id` are stripped.
- Each panel starts with `## panel <panel_id> [<start>..<end>]s`. The
  interval is optional — panels without it come back with no entry in the
  returned `intervals` dict.
- Inside a panel, `- key: value` sets `shot`, `framing`, `camera`,
  `transition`. `transition: cut` is the default and is omitted from
  output.
- Markdown image tags `![cap](src)` become `PanelImage` entries. The
  `src` prefix decides the field:
  - `artifact:<sha>` → `PanelImage(artifact_id=sha)`
  - `http://` / `https://` / `s3://` / `gs://` → `PanelImage(url=...)`
  - anything else → `PanelImage(path=...)`
- `> notes: ...` populates `PanelBody.notes`.
- Everything else inside a panel becomes part of the `caption`.

## Render to Markdown

```python
md = to_markdown(sb, panel_intervals)   # intervals is optional
```

Omit `panel_intervals` when panels haven't been pinned yet — the headings
will just say `## panel p1` without the interval. Use this when an LLM
should choose intervals.

## Parse Markdown back

```python
sb, intervals = from_markdown(md)
```

- Returns a `Storyboard` plus a `dict[panel_id, TimeInterval]`.
- Panels without a heading interval are absent from the returned dict —
  caller can pin them afterward.
- Unknown lines inside a panel fall through to the caption, so the LLM
  can write naturally and it still parses.

## LLM authoring loop

```python
from artful import to_markdown, from_markdown, save_storyboard

# 1. Show the current storyboard to the model.
prompt = f"Edit this storyboard:\n\n{to_markdown(sb, intervals)}"

# 2. Run the model, get back edited Markdown.
edited_md = run_llm(prompt)

# 3. Parse and persist.
new_sb, new_intervals = from_markdown(edited_md)
save_storyboard(new_sb, store, panel_intervals=new_intervals)
```

This loop is the reason Markdown is round-trip safe: every field that
matters is reconstructed from the text, so the LLM can rewrite freely
without dropping data.

## Generating panels from a script

When asking an LLM to **create** a storyboard from a script, give it the
exact Markdown shape and ask it to invent panel ids. Then parse and pin:

```python
sb, intervals = from_markdown(llm_output)
# If the LLM didn't include intervals, build them from a separate
# scene-timing pass and pass them at save time:
save_storyboard(sb, store, panel_intervals=my_pinned_intervals)
```

`from_markdown` won't reject a storyboard with no intervals — that's the
intended workflow for "draft now, pin later."

## Round-trip guarantees and limits

Preserved by round-trip:

- title, asset_id, style, aspect
- per-panel: panel_id, shot_id, framing, camera, transition_in, caption, notes
- images: path / url / artifact_id is reconstructed from the src prefix;
  caption is preserved
- intervals (when present in the heading)

Not preserved by round-trip:

- `PanelImage.role`. The Markdown image tag has no place to carry it —
  parsed images come back with the default role (`"thumbnail"`). If
  roles matter (e.g. distinguishing the seed image from a thumbnail),
  set them after parsing or persist via `save_storyboard` instead of
  Markdown.

## When *not* to use Markdown

- For the source-of-truth persistence layer — use `save_storyboard` into
  a `lacing` store instead. Markdown is the editing format, not the SSOT.
- When you need provenance, multiple authors, or per-panel artifacts.
  The lacing store carries that; Markdown doesn't.
