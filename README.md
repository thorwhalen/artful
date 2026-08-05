# artful

Storyboard data model and exporters — lacing-native panels along a timeline.

A *storyboard* is a sequence of *panels* along a timeline (a song, a video, a
podcast clip). Each panel pins an interval of the master asset, optionally
points at a project shot, and carries one or more images plus directorial
annotations (caption, framing, camera, transition, notes). Panels are
persisted as [lacing](https://github.com/thorwhalen/lacing) annotations, so a
storyboard is queryable, exportable, and round-trippable through every
adapter lacing already supports (TextGrid, EAF, JAMS, OTIO, WebVTT, Web
Annotation, …) without artful having to reinvent any of it.

artful is **not** the renderer. It's the panels-along-a-timeline plan that
drives a renderer: an LLM authors panels from a script, a human reviews the
contact sheet, the same panel data feeds downstream image / video generation.

## Install

```bash
pip install artful
```

Requires `pydantic>=2.6` and `lacing>=0.0.13`.

## Quick start

```python
from artful import (
    PanelBody,
    PanelImage,
    Storyboard,
    panel_intervals_from_panels,
    save_storyboard,
    load_storyboard,
)
from lacing import MemoryStore

sb = Storyboard(
    title="The Bells — v1",
    asset_id="song-asset-id-abc",
    style="noir, candlelight",
    panels=(
        PanelBody(
            panel_id="p1",
            caption="Thor at the piano",
            framing="medium",
            images=(PanelImage(path="composite.png", role="seed"),),
        ),
        PanelBody(
            panel_id="p2",
            caption="Bells over winter sky",
            framing="wide",
            camera="slow push-in",
        ),
    ),
)

# Pin each panel to a time interval (seconds on the master timeline).
intervals = panel_intervals_from_panels(
    [
        ("p1", 0.0, 4.0),
        ("p2", 4.0, 8.0),
    ]
)

store = MemoryStore()
save_storyboard(sb, store, panel_intervals=intervals)

# ... later, possibly in a different process / backend ...
loaded = load_storyboard(store, asset_id="song-asset-id-abc")
```

The store can be any `lacing.IntervalAnnotationStore` (`MemoryStore`,
`SQLiteStore`, `PostgresStore`, …); the persistence layer is lacing's.

## Authoring with LLMs (Markdown)

Markdown is artful's canonical "give an LLM a storyboard to read or write"
format. It round-trips losslessly through `to_markdown` / `from_markdown`.

```python
from artful import to_markdown, from_markdown

md = to_markdown(loaded, intervals)
# Show `md` to an LLM, let it edit panels, then…
edited_sb, edited_intervals = from_markdown(edited_md)
save_storyboard(edited_sb, store, panel_intervals=edited_intervals)
```

The Markdown shape:

```markdown
# The Bells — v1

- asset_id: `song-asset-id-abc`
- style: noir, candlelight
- aspect: 16:9

## panel p1 [0.00..4.00]s

- framing: medium

Thor at the piano

![seed](composite.png)

## panel p2 [4.00..8.00]s

- framing: wide
- camera: slow push-in

Bells over winter sky
```

## Reviewing as a contact sheet (HTML)

```python
from artful import to_html

with open("storyboard.html", "w") as f:
    f.write(to_html(loaded, intervals))
```

`to_html` produces a self-contained HTML page with embedded styles and
`<img>` tags pointing at each panel's `path` / `url`. Open it in a browser
to review.

## Data model

| Type | What it is |
|------|------------|
| `Storyboard` | Title, `asset_id` (the timeline), panels, style hint, aspect ratio. |
| `PanelBody` | One panel: `panel_id`, optional `shot_id`, images, caption, framing, camera, `transition_in`, notes. The interval lives on the lacing annotation's reference, not in the body. |
| `PanelImage` | One image for a panel — `artifact_id` (sha-256 lacing artifact ref), `url`, or `path`, plus a `role` (`thumbnail` \| `seed` \| `reference` \| `alternate`) and caption. |

All three are frozen Pydantic models with `extra="forbid"`. Importing
`artful` registers `PanelBody` against lacing under the body-schema URI
`annot://schema/storyboard-panel/v1`, so `lacing.validate_body(...)` works
out of the box.

## Why lacing-native?

Storyboards are an annotation problem: panels are intervals on a timeline
with structured bodies. Rather than invent a new persistence layer, artful
encodes each panel as a `lacing.Annotation` whose `body_schema_uri` is the
panel schema. The benefits:

- **Allen interval algebra** for free: overlaps, gaps, adjacencies.
- **Multiple storyboards over the same asset** stay separate via the
  `tier` field on each annotation.
- **Provenance tracked across edits** through lacing's `Provenance` model.
- **Format adapters** — read or write panels as TextGrid tiers, JAMS
  annotations, OTIO clips, Web Annotation JSON-LD, etc., via lacing.

A small `StoryboardMetaBody` schema (URI
`annot://schema/storyboard-meta/v1`) carries title / style / aspect as a
single timeless annotation alongside the panels.

## The shot schedule

Before there are panels there is a **shot schedule**: an ordered list of
shots, each carrying the constraints a downstream planner must respect, and
the advisory *risk flags* raised when those constraints collide with the
chosen video model's real limits.

```python
from artful import (
    RiskFlag,
    ShotEntry,
    ShotScheduleBody,
    save_shot_schedule,
    load_shot_schedule,
)

sched = ShotScheduleBody(
    schedule_id="sch-001",
    title="Scene 4 — the pub",
    model_id="fal-ai/bytedance/seedance/v1/pro/image-to-video",  # a reference
    aspect="16:9",
    resolution="720p",
    shots=(
        ShotEntry(
            shot_id="sh-01",
            description="Mairead pushes the door open.",
            characters=("Mairead",),
            shot_size="MS",
            duration_seconds_estimate=6.0,
            max_duration_seconds=8.0,
            max_characters_in_frame=1,
            take_budget=3,
            clump_id="pub-interior",
        ),
        ShotEntry(
            shot_id="sh-02",
            characters=("Mairead", "Declan"),
            duration_seconds_estimate=14.0,
            has_dialogue=True,
            risk_flags=(
                RiskFlag(
                    code="over_clip_cap",
                    message="~14s is over this model's ~10s clip cap.",
                    gotcha_id="seedance-clip-length-cap",
                ),
            ),
        ),
    ),
)

save_shot_schedule(sched, store, asset_id="song-asset-id-abc")
loaded = load_shot_schedule(store, asset_id="song-asset-id-abc")
```

Three sources of truth, deliberately kept apart:

| what | who owns it |
|------|-------------|
| What a **model** can do (`max_clip_seconds`, `single_character_recommended`, `supported_resolutions`, …) | the model registry downstream — referenced here by `model_id`, **never copied**. |
| What a **shot** requires (`max_duration_seconds`, `max_characters_in_frame`, `aspect`, `resolution`, `take_budget`) | `ShotEntry`. |
| What happens when the two **collide** | `RiskFlag` — a cached verdict, stamped with `advised_for_model_id` so a model change makes it visibly stale via `schedule.needs_advice`. |

Ordering is the tuple order of `shots` — there is deliberately no `order`
field to disagree with it, and no `character_count` field to drift from
`len(characters)`. Constraint defaults encode the safe choice:
`allow_last_frame_anchor` is `False`, because anchoring both a first and a
last frame contorts the subject mid-clip.

The schedule persists as a **single** timeless annotation under
`annot://schema/shot-schedule/v1` — a schedule exists *before* times are
pinned, which is exactly what `duration_seconds_estimate` is for.

## API surface

```python
from artful import (
    # data model
    Storyboard,
    PanelBody,
    PanelImage,
    ModelSheet,
    ShotScheduleBody,
    ShotEntry,
    RiskFlag,
    new_panel_id,
    new_shot_id,
    new_schedule_id,
    # persistence (round-trip with any lacing.IntervalAnnotationStore)
    save_storyboard,
    load_storyboard,
    panel_intervals_from_panels,
    save_shot_schedule,
    load_shot_schedule,
    load_shot_schedules,
    # exports
    to_markdown,
    from_markdown,
    to_html,
    # body-schema URIs
    PANEL_BODY_SCHEMA_URI,
    STORYBOARD_META_BODY_SCHEMA_URI,
    MODEL_SHEET_BODY_SCHEMA_URI,
    SHOT_SCHEDULE_BODY_SCHEMA_URI,
    StoryboardMetaBody,
)
```

PDF export is deferred to the optional `[pdf]` extra (reportlab).

## License

MIT
