---
name: artful
description: >
  Build, persist, and load storyboards — panels along a timeline — using the
  artful package on top of lacing. Use this skill whenever the user works
  with storyboards, panels, shots-as-panels, or timeline-pinned visual
  plans for a song / video / podcast clip. Triggers on "storyboard",
  "storyboard panel", "panel along a timeline", "PanelBody", "PanelImage",
  "save storyboard", "load storyboard", "contact sheet", "shot list as
  panels", "render storyboard images", and on any task that involves
  constructing or round-tripping a Storyboard through a lacing store.
  For Markdown round-trip with LLMs, see the `artful-markdown` skill; for
  the ordered, model-constraint-aware shot list that precedes the panels,
  see the `artful-shot-schedule` skill.
---

# artful — Storyboards on a Timeline

artful models a *storyboard* as a sequence of *panels* on a master timeline
(the song / video / clip). Each panel is persisted as a
`lacing.Annotation`, so storyboards inherit every lacing capability
(interval algebra, multiple store backends, format adapters, provenance)
for free.

Install: `pip install artful` (brings in `pydantic`, `lacing`).

## The three models you build with

```python
from artful import Storyboard, PanelBody, PanelImage
```

| Model | What it carries |
|-------|-----------------|
| `Storyboard` | `title`, `asset_id` (the timeline asset), `panels`, `style`, `aspect` |
| `PanelBody` | `panel_id`, optional `shot_id`, `images`, `caption`, `framing`, `camera`, `transition_in`, `notes` |
| `PanelImage` | One of `artifact_id` / `url` / `path`, plus `role` (a free string — by convention `thumbnail` / `seed` / `reference` / `alternate`, not validated) and `caption` |

The table lists the core fields. `PanelBody` also carries review / alternate
state (`review_status`, `active_image_index`) and the additive
narrative-to-storyboard fields (`moment_*`, `split_*`, the controlled
`shot_size` / `angle` / `movement`, and `duration_*`) — `artful/schema.py` has
the full list with per-field docs.

All three set `extra="forbid"`. The two *body* models — `PanelBody` and
`PanelImage` — are also **frozen**: build new versions with
`model_copy(update={...})` rather than mutating. `Storyboard` is a plain
in-memory view and is mutable.

Important: `PanelBody` itself does **not** carry the interval. The interval
lives on the lacing annotation's `reference` and is supplied separately at
save time via `panel_intervals`. This is so storyboards travel naturally
through lacing's interval-keyed surface.

## Build a storyboard

```python
from artful import Storyboard, PanelBody, PanelImage, new_panel_id

sb = Storyboard(
    title="The Bells — v1",
    asset_id="song-asset-id-abc",  # the master timeline this storyboard plots
    style="noir, candlelight",  # global visual-style hint
    aspect="16:9",
    panels=(
        PanelBody(
            panel_id="p1",
            shot_id="s01",  # optional: pointer to a shot in your project graph
            caption="Thor at the piano",
            framing="medium",  # wide | medium | close | ecu | insert | ots
            camera="static",  # static | slow push-in | pan-left | ...
            transition_in="cut",  # cut (default) | fade | match-cut | ...
            images=(
                PanelImage(path="composite.png", role="seed"),
                PanelImage(url="https://x/thumb.png", role="thumbnail"),
            ),
        ),
        PanelBody(panel_id=new_panel_id(), caption="Bells over winter sky"),
    ),
)
```

`new_panel_id(prefix="p")` returns a short fresh id like `"p3f7c1"`. Use it
when the LLM or pipeline is creating panels and doesn't have a stable id
already.

## Persist to a lacing store

`save_storyboard` writes each panel as one `lacing.Annotation` and adds a
single timeless meta annotation for `title` / `style` / `aspect`. You must
supply intervals separately:

```python
from artful import save_storyboard, panel_intervals_from_panels
from lacing import MemoryStore  # or SQLiteStore, PostgresStore, ...

intervals = panel_intervals_from_panels(
    [
        ("p1", 0.0, 4.0),
        ("p2", 4.0, 8.0),
    ]
)

store = MemoryStore()
save_storyboard(
    sb,
    store,
    panel_intervals=intervals,
    tier="storyboard",  # default — see "Multiple storyboards" below
    was_attributed_to="user:thor",
    was_generated_by="agent:artful",
)
```

`save_storyboard` raises `KeyError` if any panel's id is missing from
`panel_intervals` — every panel must be pinned before saving.

If you already have intervals as `lacing.TimeInterval` objects, pass them
directly as `{panel_id: TimeInterval}`; `panel_intervals_from_panels` is
just a convenience for `(panel_id, start_s, end_s)` triples.

## Load from a lacing store

```python
from artful import load_storyboard

loaded = load_storyboard(
    store,
    asset_id="song-asset-id-abc",
    tier="storyboard",  # default
)
```

`load_storyboard` filters by `asset_id` and `tier`, reconstructs each
`PanelBody`, sorts panels by interval start, and rolls the meta annotation
back into `title` / `style` / `aspect`.

## Multiple storyboards over the same asset

Use distinct `tier` values to keep multiple versions of a storyboard
side-by-side in one store:

```python
save_storyboard(sb_v1, store, panel_intervals=ivs, tier="storyboard")
save_storyboard(sb_v2, store, panel_intervals=ivs, tier="storyboard-v2")

load_storyboard(store, asset_id=asset_id, tier="storyboard-v2")
```

## The body schema is registered with lacing

Importing `artful` registers `PanelBody` under
`PANEL_BODY_SCHEMA_URI == "annot://schema/storyboard-panel/v1"`. That means
arbitrary lacing tooling validates panel bodies for free:

```python
from lacing import validate_body
from artful import PANEL_BODY_SCHEMA_URI

panel = validate_body(some_body_dict, PANEL_BODY_SCHEMA_URI)
# returns a validated PanelBody; raises on unknown fields or bad types
```

Same story for `STORYBOARD_META_BODY_SCHEMA_URI` →
`"annot://schema/storyboard-meta/v1"` (title / style / aspect).

## HTML contact sheet (review)

For a quick browser review:

```python
from artful import to_html

with open("storyboard.html", "w") as f:
    f.write(to_html(sb, intervals))  # intervals is optional
```

The output is a self-contained HTML page; image refs become `<img>` tags
pointing at `path` / `url`. Special characters are escaped.

## When to use what

| Task | Use |
|------|-----|
| Plan shots *before* panels exist, against a video model's limits | `ShotScheduleBody` (see the `artful-shot-schedule` skill) |
| Author panels in code or from a pipeline | Build `Storyboard` directly |
| Hand-edit or LLM-edit panels as text | `to_markdown` / `from_markdown` (see the `artful-markdown` skill) |
| Persist for later, share across machines | `save_storyboard` into a lacing store |
| Review in a browser | `to_html` |
| Feed a renderer (e.g. `nw.render_storyboard_images`) | The `PanelImage(role="seed")` images |

## Common gotchas

- **Frozen models.** Build a new `PanelBody` with `panel.model_copy(update=...)`; don't mutate fields.
- **Intervals are separate from the body.** Always pair a panel with an interval at save time; round-tripping via `to_markdown` keeps them paired.
- **`asset_id` matters.** `load_storyboard` filters by it. Use the asset id of the master timeline (the song / video the panels live on), not of any image.
- **Use `PanelImage.artifact_id` for cross-machine identity.** It matches `lacing.Artifact.asset_id` (sha-256 of the bytes). `path` / `url` are fine for local work but don't survive moves.
