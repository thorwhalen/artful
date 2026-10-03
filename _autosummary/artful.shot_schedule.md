# artful.shot_schedule

Shot schedule — an ordered, model-constraint-aware shot list.

A *shot schedule* is the planning document that sits between a scene
breakdown and a storyboard: an ordered list of shots, each carrying the
constraints a downstream planner must respect (clip-length cap, how many
characters may share the frame, aspect / resolution, how many takes the
shot is allowed to burn) plus the advisory *risk flags* raised when those
constraints collide with the chosen video model’s real limits.

Persisted as a **single** `lacing.Annotation` with body schema
`annot://schema/shot-schedule/v1`. One annotation, not one per shot,
because a schedule exists *before* times are pinned — the ordering is the
tuple order of `ShotScheduleBody.shots`, not an interval sort.

## Three sources of truth, deliberately kept apart

| what                   | who owns it                                                                                                                                                                                                                                                  |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| what a *model* can do  | `falaw`’s model registry<br/>(`max_clip_seconds`,<br/>`single_character_recommended`,<br/>`supported_resolutions`, …). Referenced<br/>here by `ShotScheduleBody.model_id`<br/>— **never copied**.                                                            |
| what a *shot* requires | this schema (`max_duration_seconds`,<br/>`max_characters_in_frame`, `aspect`,<br/>`resolution`, `take_budget`).                                                                                                                                              |
| what happens when they | [`RiskFlag`](#artful.shot_schedule.RiskFlag) — the cached verdict of                                                                                                                                                                            |
| collide                | comparing the two. Computed by reelee’s<br/>shot advisor; stamped with<br/>`ShotScheduleBody.advised_for_model_id`<br/>so a model change makes the flags visibly<br/>stale ([`ShotScheduleBody.needs_advice`](#artful.shot_schedule.ShotScheduleBody.needs_advice)). |

Vocabulary is shared, not re-invented: shot grammar (`shot_size` /
`angle` / `movement`) reuses the controlled taxonomies defined in
[`artful.schema`](artful.schema.md#module-artful.schema); `duration_seconds_estimate` / `duration_source`
reuse the names already on [`artful.PanelBody`](artful.md#artful.PanelBody); characters are named
by their `character-ref` name (the schema for `character-ref/v1` lives
in `nw`), matching `artful.PanelBody.moment_focal_character_ref`;
and `RiskFlag.gotcha_id` points into reelee’s tool-gotchas registry
rather than restating the mitigation prose here.

Plan vs realization: when a shot entry names a `panel_id` / `shot_id`,
those annotations are authoritative for the *realized* shot. The grammar
fields here are the *planned* values — what the schedule intends before a
panel exists.

### Module Attributes

| [`SHOT_SCHEDULE_TIER`](#artful.shot_schedule.SHOT_SCHEDULE_TIER)   | Default lacing tier for persisted schedules — so several schedules over one asset (a draft and a revision, say) stay distinguishable by tier.   |
|-----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| [`RiskCode`](#artful.shot_schedule.RiskCode)             | Controlled vocabulary of advisory flags a shot advisor may raise.                                                                               |
| [`RiskSeverity`](#artful.shot_schedule.RiskSeverity)         | Matches the reelee shot advisor's `ShotWarning.severity` exactly.                                                                               |

### Functions

| [`load_shot_schedule`](#artful.shot_schedule.load_shot_schedule)(store, \*, asset_id[, ...])    | One schedule, or None when there is no match.                      |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`load_shot_schedules`](#artful.shot_schedule.load_shot_schedules)(store, \*, asset_id[, tier])  | Every schedule in `store` for `asset_id` / `tier`, in store order. |
| [`new_schedule_id`](#artful.shot_schedule.new_schedule_id)([prefix])                         | Generate a fresh short schedule id (e.g. `"sch3f7c1"`).            |
| [`new_shot_id`](#artful.shot_schedule.new_shot_id)([prefix])                             | Generate a fresh short shot id (e.g. `"sh3f7c1"`).                 |
| [`save_shot_schedule`](#artful.shot_schedule.save_shot_schedule)(schedule, store, \*, asset_id) | Persist `schedule` into `store` as one timeless annotation.        |

### Classes

| [`RiskFlag`](#artful.shot_schedule.RiskFlag)(\*\*data)         | One advisory warning attached to a shot (or to the whole schedule).   |
|-----------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`ShotEntry`](#artful.shot_schedule.ShotEntry)(\*\*data)        | One row of a shot schedule: what to shoot, and what bounds it.        |
| [`ShotScheduleBody`](#artful.shot_schedule.ShotScheduleBody)(\*\*data) | The body of a shot-schedule annotation — the ordered shot list.       |

### artful.shot_schedule.RiskCode

Controlled vocabulary of advisory flags a shot advisor may raise.

`over_clip_cap` and `multi_character` are **the same strings** the
reelee shot advisor already emits as `ShotWarning.code`; do not rename
them — one code vocabulary across the federation, not two. The rest name
pitfalls that are already curated entries in reelee’s tool-gotchas
registry (`seedance-first-last-frame-contortion`,
`seedance-dialogue-plus-action-degrades`, `regen-full-price`,
`resolution-cost-tradeoff`, `aspect-ratio-crop-surprise`).

Closed vocabulary, per artful convention: adding a code is an additive
schema change, made deliberately.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘over_clip_cap’, ‘multi_character’, ‘first_last_frame’, ‘dialogue_plus_action’, ‘over_take_budget’, ‘unsupported_resolution’, ‘mixed_aspect_ratios’]

### *class* artful.shot_schedule.RiskFlag(\*\*data)

Bases: `BaseModel`

One advisory warning attached to a shot (or to the whole schedule).

A *cached verdict*, not a constraint: it records that this shot’s
requirements collided with the limits of the model named by
`ShotScheduleBody.advised_for_model_id`. Re-advise after
changing the model — [`ShotScheduleBody.needs_advice`](#artful.shot_schedule.ShotScheduleBody.needs_advice) says when.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### artful.shot_schedule.RiskSeverity

Matches the reelee shot advisor’s `ShotWarning.severity` exactly.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[‘info’, ‘warn’]

### artful.shot_schedule.SHOT_SCHEDULE_TIER *= 'shot-schedule'*

Default lacing tier for persisted schedules — so several schedules over
one asset (a draft and a revision, say) stay distinguishable by tier.

### *class* artful.shot_schedule.ShotEntry(\*\*data)

Bases: `BaseModel`

One row of a shot schedule: what to shoot, and what bounds it.

Position in `ShotScheduleBody.shots` **is** the shot’s order —
there is deliberately no `order` field to disagree with it.

#### model_config *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [`ConfigDict`][pydantic.config.ConfigDict].

### *class* artful.shot_schedule.ShotScheduleBody(\*\*data)

Bases: `BaseModel`

The body of a shot-schedule annotation — the ordered shot list.

The annotation’s `reference` carries the `asset_id` this schedule
plans, so it is not duplicated here (same split as
[`artful.PanelBody`](artful.md#artful.PanelBody)).

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
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ShotEntry`](#artful.shot_schedule.ShotEntry)]

### artful.shot_schedule.load_shot_schedule(store, , asset_id, schedule_id=None, tier='shot-schedule')

One schedule, or None when there is no match.

With `schedule_id` given, returns that schedule. Without it, returns
the first schedule found for `asset_id` / `tier` — convenient for
the common one-schedule-per-asset case.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`ShotScheduleBody`](#artful.shot_schedule.ShotScheduleBody)]

### artful.shot_schedule.load_shot_schedules(store, , asset_id, tier='shot-schedule')

Every schedule in `store` for `asset_id` / `tier`, in store order.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`ShotScheduleBody`](#artful.shot_schedule.ShotScheduleBody)]

### artful.shot_schedule.new_schedule_id(prefix='sch')

Generate a fresh short schedule id (e.g. `"sch3f7c1"`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.shot_schedule.new_shot_id(prefix='sh')

Generate a fresh short shot id (e.g. `"sh3f7c1"`).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### artful.shot_schedule.save_shot_schedule(schedule, store, , asset_id, tier='shot-schedule', was_attributed_to='user:unknown', was_generated_by='agent:artful')

Persist `schedule` into `store` as one timeless annotation.

Like [`artful.save_storyboard()`](artful.md#artful.save_storyboard) this *appends* — saving twice adds
a second annotation rather than replacing the first, so a store can
hold a schedule’s revision history. Use `tier` (or `schedule_id`)
to tell revisions apart on load.

* **Parameters:**
  * **schedule** ([`ShotScheduleBody`](#artful.shot_schedule.ShotScheduleBody)) – The [`ShotScheduleBody`](#artful.shot_schedule.ShotScheduleBody) to persist.
  * **store** (`IntervalAnnotationStore`) – Any `lacing.IntervalAnnotationStore`.
  * **asset_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The asset this schedule plans (goes on the annotation’s
    `reference`, not into the body).
  * **tier** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Tier name for the persisted annotation.
  * **was_generated_by** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Provenance fields.
* **Return type:**
  `Annotation`
* **Returns:**
  The persisted `lacing.Annotation`.
