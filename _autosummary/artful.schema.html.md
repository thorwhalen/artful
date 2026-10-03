# artful.schema

Storyboard schema — typed Panels along a timeline, lacing-native.

A *storyboard* is a sequence of *panels*. Each panel:

- Spans a time interval on a project’s master timeline (song time, scene
  time, podcast clip time).
- Optionally points at a shot (or other unit) in the project graph.
- Carries one or more *image references* — generated stills, hand drawings,
  screenshots, or pointers to a `lacing.Artifact` in storage.
- Carries directorial annotations: caption, framing, camera, transition,
  notes.

Panels are persisted as `lacing.Annotation` records with body schema
`annot://schema/storyboard-panel/v1`, registered into lacing on package
import. That means a storyboard is queryable, exportable, and round-trippable
through every adapter lacing already supports (TextGrid, EAF, JAMS, OTIO,
WebVTT, Web Annotation), with provenance tracked across edits.

A storyboard is **not** the rendered video — it’s the panels-along-a-timeline
plan that drives the renderer. Use cases:

- A human draws or arranges panels; an agent renders the panel images via
  `nw.render_storyboard_images`.
- An agent generates panels from a script; a human reviews them as a PDF.
- The same panel data populates both a printed contact sheet and the
  i2v / composite_lipsync seed images for downstream rendering.

### Module Attributes

| [`ReviewStatus`](#artful.schema.ReviewStatus)    | Review status of a storyboard panel.                             |
|------------------------------------------------------------------|------------------------------------------------------------------|
| [`MomentHeuristic`](#artful.schema.MomentHeuristic) | Spec §7.2 iconic-frame heuristics.                               |
| [`MomentTiming`](#artful.schema.MomentTiming)    | Spec §7.2 — where in the implied motion the depicted frame sits. |
| [`ShotSize`](#artful.schema.ShotSize)        | Spec §6.3 shot-size taxonomy.                                    |
| [`Angle`](#artful.schema.Angle)           | Spec §6.3 / §9.3 angle taxonomy.                                 |
| [`Movement`](#artful.schema.Movement)        | Spec §6.3 movement taxonomy.                                     |
| [`DurationSource`](#artful.schema.DurationSource)  | Spec §7.5 — provenance of a panel's duration field.              |
| [`ModelSheetView`](#artful.schema.ModelSheetView)  | Canonical model-sheet views (spec §7.4 conventions).             |

### Functions

| [`new_panel_id`](#artful.schema.new_panel_id)([prefix])   | Generate a fresh short panel id (e.g. `"p3f7c1"`).   |
|---------------------------------------------------------------------------|------------------------------------------------------|

### Classes

| [`ModelSheet`](#artful.schema.ModelSheet)(\*\*data)   | The body of a model-sheet annotation — a character's canonical turnaround, expression set, and supporting metadata.   |
|-------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| [`PanelBody`](#artful.schema.PanelBody)(\*\*data)    | The body of a storyboard-panel annotation.                                                                            |
| [`PanelImage`](#artful.schema.PanelImage)(\*\*data)   | One image associated with a panel.                                                                                    |
| [`Storyboard`](#artful.schema.Storyboard)(\*\*data)   | A typed view over a sequence of panel annotations.                                                                    |

### artful.schema.Angle

Spec §6.3 / §9.3 angle taxonomy. Controlled vocabulary — distinct from the
free-text `PanelBody.camera` field.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘EYE_LEVEL’, ‘HIGH’, ‘LOW’, ‘DUTCH’, ‘BIRDS_EYE’, ‘WORMS_EYE’, ‘PROFILE’, ‘THREE_QUARTER’, ‘OTS’, ‘POV’]

### artful.schema.DurationSource

Spec §7.5 — provenance of a panel’s duration field. `manual`
indicates the user overrode the estimate.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘estimate’, ‘from_voiceover’, ‘from_clip’, ‘manual’]

### *class* artful.schema.ModelSheet(\*\*data)

Bases: `BaseModel`

The body of a model-sheet annotation — a character’s canonical
turnaround, expression set, and supporting metadata.

Produced by `character_to_modelsheet.<flavor>.<model>` (spec §7.4).
Lives in artful (next to PanelBody) because it is a storyboard-adjacent
asset: model sheets feed into per-panel renders as reference images,
and the inspector surfaces them alongside the panels they conditioned.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### artful.schema.ModelSheetView

Canonical model-sheet views (spec §7.4 conventions).

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘front’, ‘three_quarter_front’, ‘side_left’, ‘side_right’, ‘three_quarter_back’, ‘back’]

### artful.schema.MomentHeuristic

Spec §7.2 iconic-frame heuristics. `entry_for_clip` is the
mandatory choice for `ai_cinematic_clip` output intents (where the
video model interpolates forward from the depicted frame).

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘decisive_composition’, ‘apex_of_action’, ‘just_before_recognition’, ‘held_breath’, ‘reaction_not_action’, ‘entry_for_clip’, ‘expression_over_action’, ‘silhouette_test’, ‘eyeline_contact’]

### artful.schema.MomentTiming

Spec §7.2 — where in the implied motion the depicted frame sits.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘entry’, ‘mid’, ‘apex’, ‘exit’]

### artful.schema.Movement

Spec §6.3 movement taxonomy. `LOCKED` is the default in practice.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘LOCKED’, ‘PAN’, ‘TILT’, ‘DOLLY_IN’, ‘DOLLY_OUT’, ‘TRUCK’, ‘PEDESTAL’, ‘ZOOM’, ‘CRANE’, ‘HANDHELD’, ‘WHIP_PAN’, ‘DOLLY_ZOOM’]

### *class* artful.schema.PanelBody(\*\*data)

Bases: `BaseModel`

The body of a storyboard-panel annotation.

Persisted as the `body` dict of a `lacing.Annotation` whose
`body_schema_uri` is `PANEL_BODY_SCHEMA_URI`.

The annotation’s `reference` (a `lacing.MediaRef`) carries the
interval — i.e. the time span this panel covers — so we don’t duplicate
interval information here.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.schema.PanelImage(\*\*data)

Bases: `BaseModel`

One image associated with a panel.

Either an `artifact_id` (pointing into lacing’s Artifact registry by
content hash) or a direct `url` / `path` is required. `role`
distinguishes “this is the thumbnail you show on the contact sheet”
from “this is the seed image for the renderer.”

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### artful.schema.ReviewStatus

Review status of a storyboard panel. Defaults to `"unreviewed"`;
the FE Kanban view + per-panel review badge consume this. v0.3
persisted-review-status field — backward-compatible (existing dump
files without the field get the default).

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘unreviewed’, ‘approved’, ‘needs-revision’, ‘rejected’]

### artful.schema.ShotSize

Spec §6.3 shot-size taxonomy. Controlled vocabulary — distinct from the
free-text `PanelBody.framing` field. This is the single source of truth
for the storyboard-panel schema; `reelee.bodies.shot` re-exports these so the
shot-grammar advisor and the panel body share one vocabulary.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘ECU’, ‘CU’, ‘MCU’, ‘MS’, ‘MWS’, ‘WS’, ‘LS’, ‘ELS’, ‘INSERT’, ‘TWO_SHOT’, ‘THREE_SHOT’, ‘GROUP’, ‘MASTER’]

### *class* artful.schema.Storyboard(\*\*data)

Bases: `BaseModel`

A typed view over a sequence of panel annotations.

Storyboards are *constructed* from in-memory data and *persisted* by
writing each panel as a lacing `Annotation`. Use the helpers in
[`artful.store`](artful.store.html.md#module-artful.store) to round-trip with a lacing store.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid'}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### artful.schema.new_panel_id(prefix='p')

Generate a fresh short panel id (e.g. `"p3f7c1"`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
