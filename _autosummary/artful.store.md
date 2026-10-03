# artful.store

Round-trip a `Storyboard` through a lacing store.

Persistence model:

- Each `PanelBody` is stored as a `lacing.Annotation` whose
  `body` is the panel body, `body_schema_uri` is
  `PANEL_BODY_SCHEMA_URI`, `reference` is a `lacing.MediaRef`
  > (asset_id of the timeline + the panel’s interval), and `tier` is the
  > storyboard title (or “storyboard” by default).
- The storyboard’s `style` and `aspect` (no per-panel interval) are
  stored as one *timeless* annotation tagged with the same tier name and a
  small distinct body schema URI.

This way every adapter lacing already supports (TextGrid, EAF, JAMS, OTIO,
WebVTT, Web Annotation, JAMS, Label Studio, …) can round-trip a storyboard
unchanged. Apps add storyboard semantics by reading panels via
[`load_storyboard()`](#artful.store.load_storyboard); the underlying lacing store stays the single SSOT.

### Functions

| [`load_storyboard`](#artful.store.load_storyboard)(store, \*, asset_id[, tier])       | Read panels from `store` and reconstruct a `Storyboard`.                                                            |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| [`make_prov`](#artful.store.make_prov)(was_generated_by, was_attributed_to)     | Build the create-activity `lacing.Provenance` artful stamps on every annotation it persists.                        |
| [`panel_intervals_from_panels`](#artful.store.panel_intervals_from_panels)(panels)                | Convenience: build the panel_intervals dict for [`save_storyboard()`](#artful.store.save_storyboard). |
| [`save_storyboard`](#artful.store.save_storyboard)(storyboard, store, \*, ...[, ...]) | Persist `storyboard` into `store`.                                                                                  |

### Classes

| [`StoryboardMetaBody`](#artful.store.StoryboardMetaBody)(\*\*data)   |    |
|---------------------------------------------------------------------------------|----|

### *class* artful.store.StoryboardMetaBody(\*\*data)

Bases: `BaseModel`

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### artful.store.load_storyboard(store, , asset_id, tier='storyboard')

Read panels from `store` and reconstruct a `Storyboard`.

Filters by `tier` (default `"storyboard"`) and `asset_id` (so a
store holding multiple storyboards over multiple assets stays clean).
Panels are returned ordered by interval start.

* **Return type:**
  [`Storyboard`](artful.schema.md#artful.schema.Storyboard)

### artful.store.make_prov(was_generated_by, was_attributed_to)

Build the create-activity `lacing.Provenance` artful stamps on
every annotation it persists. Package-internal (not in `artful.__all__`);
shared by [`artful.store`](#module-artful.store) and [`artful.shot_schedule`](artful.shot_schedule.md#module-artful.shot_schedule).

* **Return type:**
  `Provenance`

### artful.store.panel_intervals_from_panels(panels)

Convenience: build the panel_intervals dict for [`save_storyboard()`](#artful.store.save_storyboard).

Takes an iterable of `(panel_id, start_s, end_s)` triples. Returns a
dict keyed by panel_id with TimeInterval values.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TimeInterval`]

### artful.store.save_storyboard(storyboard, store, , panel_intervals, tier='storyboard', was_attributed_to='user:unknown', was_generated_by='agent:artful')

Persist `storyboard` into `store`.

* **Parameters:**
  * **storyboard** ([`Storyboard`](artful.schema.md#artful.schema.Storyboard)) – The `Storyboard` to persist.
  * **store** (`IntervalAnnotationStore`) – A lacing store (any `IntervalAnnotationStore`).
  * **panel_intervals** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), `TimeInterval`]) – Per-panel-id mapping to a `lacing.TimeInterval`.
    Required because `PanelBody` itself does not carry the
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
