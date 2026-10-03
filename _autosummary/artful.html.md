# artful

artful — Storyboard data model and exporters.

A *storyboard* is a sequence of *panels* along a timeline. Each panel pins
an interval of the master asset (a song, video, podcast clip), optionally
points at a project shot, and carries one or more images plus directorial
annotations.

Panels are persisted as `lacing.Annotation` records with body schema
`annot://schema/storyboard-panel/v1`. That means a storyboard is queryable
with lacing’s full toolkit (Allen interval algebra, store backends, format
adapters) without artful having to reinvent any of it.

Alongside the storyboard, artful owns two storyboard-adjacent bodies:
[`ModelSheet`](#artful.ModelSheet) (a character’s canonical turnaround) and
[`ShotScheduleBody`](#artful.ShotScheduleBody) (the ordered, model-constraint-aware shot list
that precedes the panels — see [`artful.shot_schedule`](artful.shot_schedule.html.md#module-artful.shot_schedule)).

Public surface:

- [`Storyboard`](#artful.Storyboard), [`PanelBody`](#artful.PanelBody), [`PanelImage`](#artful.PanelImage) — Pydantic
  models for in-memory work.
- [`save_storyboard()`](#artful.save_storyboard) / [`load_storyboard()`](#artful.load_storyboard) — round-trip with any
  `lacing.IntervalAnnotationStore`.
- [`to_markdown()`](#artful.to_markdown) / [`from_markdown()`](#artful.from_markdown) — round-trip Markdown
  (the canonical format for LLM authoring).
- [`to_html()`](#artful.to_html) — self-contained HTML contact sheet for review.
- [`ShotScheduleBody`](#artful.ShotScheduleBody), [`ShotEntry`](#artful.ShotEntry), [`RiskFlag`](#artful.RiskFlag) +
  [`save_shot_schedule()`](#artful.save_shot_schedule) / [`load_shot_schedule()`](#artful.load_shot_schedule) — the shot
  > schedule and its store round-trip.

### Functions

| [`from_markdown`](#artful.from_markdown)(text)                                | Parse [`to_markdown()`](#artful.to_markdown)'s output back into a Storyboard + intervals.   |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| [`load_shot_schedule`](#artful.load_shot_schedule)(store, \*, asset_id[, ...])     | One schedule, or None when there is no match.                                                                       |
| [`load_shot_schedules`](#artful.load_shot_schedules)(store, \*, asset_id[, tier])   | Every schedule in `store` for `asset_id` / `tier`, in store order.                                                  |
| [`load_storyboard`](#artful.load_storyboard)(store, \*, asset_id[, tier])       | Read panels from `store` and reconstruct a [`Storyboard`](#artful.Storyboard).             |
| [`new_panel_id`](#artful.new_panel_id)([prefix])                             | Generate a fresh short panel id (e.g. `"p3f7c1"`).                                                                  |
| [`new_schedule_id`](#artful.new_schedule_id)([prefix])                          | Generate a fresh short schedule id (e.g. `"sch3f7c1"`).                                                             |
| [`new_shot_id`](#artful.new_shot_id)([prefix])                              | Generate a fresh short shot id (e.g. `"sh3f7c1"`).                                                                  |
| [`panel_intervals_from_panels`](#artful.panel_intervals_from_panels)(panels)                | Convenience: build the panel_intervals dict for [`save_storyboard()`](#artful.save_storyboard). |
| [`save_shot_schedule`](#artful.save_shot_schedule)(schedule, store, \*, asset_id)  | Persist `schedule` into `store` as one timeless annotation.                                                         |
| [`save_storyboard`](#artful.save_storyboard)(storyboard, store, \*, ...[, ...]) | Persist `storyboard` into `store`.                                                                                  |
| [`to_html`](#artful.to_html)(storyboard[, panel_intervals])             | Render a self-contained HTML contact sheet.                                                                         |
| [`to_markdown`](#artful.to_markdown)(storyboard[, panel_intervals])         | Render `storyboard` as Markdown.                                                                                    |

### Classes

| [`ModelSheet`](#artful.ModelSheet)(\*\*data)         | The body of a model-sheet annotation — a character's canonical turnaround, expression set, and supporting metadata.   |
|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| [`PanelBody`](#artful.PanelBody)(\*\*data)          | The body of a storyboard-panel annotation.                                                                            |
| [`PanelImage`](#artful.PanelImage)(\*\*data)         | One image associated with a panel.                                                                                    |
| [`RiskFlag`](#artful.RiskFlag)(\*\*data)           | One advisory warning attached to a shot (or to the whole schedule).                                                   |
| [`ShotEntry`](#artful.ShotEntry)(\*\*data)          | One row of a shot schedule: what to shoot, and what bounds it.                                                        |
| [`ShotScheduleBody`](#artful.ShotScheduleBody)(\*\*data)   | The body of a shot-schedule annotation — the ordered shot list.                                                       |
| [`Storyboard`](#artful.Storyboard)(\*\*data)         | A typed view over a sequence of panel annotations.                                                                    |
| [`StoryboardMetaBody`](#artful.StoryboardMetaBody)(\*\*data) |                                                                                                                       |

### *class* artful.ModelSheet(\*\*data)

Bases: `BaseModel`

The body of a model-sheet annotation — a character’s canonical
turnaround, expression set, and supporting metadata.

Produced by `character_to_modelsheet.<flavor>.<model>` (spec §7.4).
Lives in artful (next to PanelBody) because it is a storyboard-adjacent
asset: model sheets feed into per-panel renders as reference images,
and the inspector surfaces them alongside the panels they conditioned.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.PanelBody(\*\*data)

Bases: `BaseModel`

The body of a storyboard-panel annotation.

Persisted as the `body` dict of a `lacing.Annotation` whose
`body_schema_uri` is `PANEL_BODY_SCHEMA_URI`.

The annotation’s `reference` (a `lacing.MediaRef`) carries the
interval — i.e. the time span this panel covers — so we don’t duplicate
interval information here.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.PanelImage(\*\*data)

Bases: `BaseModel`

One image associated with a panel.

Either an `artifact_id` (pointing into lacing’s Artifact registry by
content hash) or a direct `url` / `path` is required. `role`
distinguishes “this is the thumbnail you show on the contact sheet”
from “this is the seed image for the renderer.”

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.RiskFlag(\*\*data)

Bases: `BaseModel`

One advisory warning attached to a shot (or to the whole schedule).

A *cached verdict*, not a constraint: it records that this shot’s
requirements collided with the limits of the model named by
`ShotScheduleBody.advised_for_model_id`. Re-advise after
changing the model — [`ShotScheduleBody.needs_advice`](#artful.ShotScheduleBody.needs_advice) says when.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.ShotEntry(\*\*data)

Bases: `BaseModel`

One row of a shot schedule: what to shoot, and what bounds it.

Position in `ShotScheduleBody.shots` **is** the shot’s order —
there is deliberately no `order` field to disagree with it.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.ShotScheduleBody(\*\*data)

Bases: `BaseModel`

The body of a shot-schedule annotation — the ordered shot list.

The annotation’s `reference` carries the `asset_id` this schedule
plans, so it is not duplicated here (same split as
[`artful.PanelBody`](#artful.PanelBody)).

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

#### *property* needs_advice *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

True when the risk flags do not (or no longer) match `model_id`.

A schedule with no `model_id` cannot be advised, so it never
*needs* advice; one whose model changed since it was advised always
does.

#### shot(shot_id)

The entry with `shot_id`, or None. Mirrors `Storyboard.panel`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ShotEntry`](artful.shot_schedule.html.md#artful.shot_schedule.ShotEntry)]

### *class* artful.Storyboard(\*\*data)

Bases: `BaseModel`

A typed view over a sequence of panel annotations.

Storyboards are *constructed* from in-memory data and *persisted* by
writing each panel as a lacing `Annotation`. Use the helpers in
[`artful.store`](artful.store.html.md#module-artful.store) to round-trip with a lacing store.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid'}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.StoryboardMetaBody(\*\*data)

Bases: `BaseModel`

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### artful.from_markdown(text)

Parse [`to_markdown()`](#artful.to_markdown)’s output back into a Storyboard + intervals.

Lines that don’t match a known shape are appended to the current panel’s
caption. Panels without an interval in the heading are returned with
no entry in the intervals dict (caller can pin them later).

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Storyboard`](artful.schema.html.md#artful.schema.Storyboard), [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TimeInterval`]]

### artful.load_shot_schedule(store, , asset_id, schedule_id=None, tier='shot-schedule')

One schedule, or None when there is no match.

With `schedule_id` given, returns that schedule. Without it, returns
the first schedule found for `asset_id` / `tier` — convenient for
the common one-schedule-per-asset case.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ShotScheduleBody`](artful.shot_schedule.html.md#artful.shot_schedule.ShotScheduleBody)]

### artful.load_shot_schedules(store, , asset_id, tier='shot-schedule')

Every schedule in `store` for `asset_id` / `tier`, in store order.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ShotScheduleBody`](artful.shot_schedule.html.md#artful.shot_schedule.ShotScheduleBody)]

### artful.load_storyboard(store, , asset_id, tier='storyboard')

Read panels from `store` and reconstruct a [`Storyboard`](#artful.Storyboard).

Filters by `tier` (default `"storyboard"`) and `asset_id` (so a
store holding multiple storyboards over multiple assets stays clean).
Panels are returned ordered by interval start.

* **Return type:**
  [`Storyboard`](artful.schema.html.md#artful.schema.Storyboard)

### artful.new_panel_id(prefix='p')

Generate a fresh short panel id (e.g. `"p3f7c1"`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.new_schedule_id(prefix='sch')

Generate a fresh short schedule id (e.g. `"sch3f7c1"`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.new_shot_id(prefix='sh')

Generate a fresh short shot id (e.g. `"sh3f7c1"`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.panel_intervals_from_panels(panels)

Convenience: build the panel_intervals dict for [`save_storyboard()`](#artful.save_storyboard).

Takes an iterable of `(panel_id, start_s, end_s)` triples. Returns a
dict keyed by panel_id with TimeInterval values.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TimeInterval`]

### artful.save_shot_schedule(schedule, store, , asset_id, tier='shot-schedule', was_attributed_to='user:unknown', was_generated_by='agent:artful')

Persist `schedule` into `store` as one timeless annotation.

Like [`artful.save_storyboard()`](#artful.save_storyboard) this *appends* — saving twice adds
a second annotation rather than replacing the first, so a store can
hold a schedule’s revision history. Use `tier` (or `schedule_id`)
to tell revisions apart on load.

* **Parameters:**
  * **schedule** ([`ShotScheduleBody`](artful.shot_schedule.html.md#artful.shot_schedule.ShotScheduleBody)) – The [`ShotScheduleBody`](#artful.ShotScheduleBody) to persist.
  * **store** (`IntervalAnnotationStore`) – Any `lacing.IntervalAnnotationStore`.
  * **asset_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The asset this schedule plans (goes on the annotation’s
    `reference`, not into the body).
  * **tier** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Tier name for the persisted annotation.
  * **was_generated_by** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Provenance fields.
* **Return type:**
  `Annotation`
* **Returns:**
  The persisted `lacing.Annotation`.

### artful.save_storyboard(storyboard, store, , panel_intervals, tier='storyboard', was_attributed_to='user:unknown', was_generated_by='agent:artful')

Persist `storyboard` into `store`.

* **Parameters:**
  * **storyboard** ([`Storyboard`](artful.schema.html.md#artful.schema.Storyboard)) – The [`Storyboard`](#artful.Storyboard) to persist.
  * **store** (`IntervalAnnotationStore`) – A lacing store (any `IntervalAnnotationStore`).
  * **panel_intervals** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TimeInterval`]) – Per-panel-id mapping to a `lacing.TimeInterval`.
    Required because [`PanelBody`](#artful.PanelBody) itself does not carry the
    interval (it lives on the annotation’s reference); the caller must
    tell us which time span each panel covers.
  * **tier** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Tier name for the persisted annotations. Defaults to
    `"storyboard"` so multiple storyboards over the same asset can
    be distinguished by tier.
  * **was_generated_by** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Provenance fields applied to
    every persisted annotation.
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[`Annotation`]
* **Returns:**
  The list of persisted `Annotation` instances (panels, then meta).

### artful.to_html(storyboard, panel_intervals=None)

Render a self-contained HTML contact sheet.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.to_markdown(storyboard, panel_intervals=None)

Render `storyboard` as Markdown.

If `panel_intervals` is given, each panel’s heading includes its
`[start..end]s` interval. If not, only ids are shown — useful when
the intervals haven’t been pinned yet.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### Modules

| [`exports`](artful.exports.html.md#module-artful.exports)             | Storyboard exporters: Markdown ↔ HTML ↔ Storyboard.                                              |
|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`schema`](artful.schema.html.md#module-artful.schema)               | Storyboard schema — typed Panels along a timeline, lacing-native.                                |
| [`shot_schedule`](artful.shot_schedule.html.md#module-artful.shot_schedule) | Shot schedule — an ordered, model-constraint-aware shot list.                                    |
| [`store`](artful.store.html.md#module-artful.store)                 | Round-trip a [`Storyboard`](#artful.Storyboard) through a lacing store. |
