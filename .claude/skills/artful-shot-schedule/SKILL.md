---
name: artful-shot-schedule
description: >
  Build, persist, and reason about a shot schedule — an ordered,
  model-constraint-aware shot list — with artful's `shot-schedule/v1` body
  schema. Use this skill whenever the user plans shots against a video
  model's real limits: clip-length caps, how many characters may share a
  frame, aspect / resolution choices, take budgets, or batching shots into
  clumps. Triggers on "shot schedule", "shot list", "shot-list builder",
  "how long can this clip be", "clip cap", "too many characters in the
  shot", "single character per shot", "take budget", "clump", "risk flags",
  "ShotScheduleBody", "ShotEntry", "RiskFlag", "advise the shots", and on
  any task that plans shots *before* panels exist. For the panels
  themselves see the `artful` skill; for Markdown authoring see
  `artful-markdown`.
---

# artful — the shot schedule

A **shot schedule** is the planning document that sits between a scene
breakdown and a storyboard: an ordered list of shots, each carrying the
constraints a downstream planner must respect, plus the advisory *risk
flags* raised when those constraints collide with the chosen video model's
real limits.

```python
from artful import ShotScheduleBody, ShotEntry, RiskFlag
```

It exists *before* times are pinned — that is why the schedule persists as
one **timeless** annotation rather than one annotation per shot, and why
durations here are plain-float estimates rather than `RationalTime`.

## The one thing to get right: three sources of truth, kept apart

This is the mistake to avoid. Do **not** copy a model's limit table into a
schedule.

| what | who owns it | how the schedule sees it |
|---|---|---|
| What a **model** can do — `max_clip_seconds`, `single_character_recommended`, `supported_resolutions`, `default_negative_prompt` | the fal model registry (`falaw.model_constraints`) | referenced by `ShotScheduleBody.model_id`, **never copied** |
| What a **shot** requires — `max_duration_seconds`, `max_characters_in_frame`, `aspect`, `resolution`, `allow_last_frame_anchor`, `take_budget` | `ShotEntry` — this *is* the source of truth | set it directly |
| What happens when the two **collide** | `RiskFlag` — a cached advisory verdict | `risk_flags`, stamped with `advised_for_model_id` |

A `max_clip_seconds` field on a `ShotEntry` would be a second source of
truth that silently goes stale when the registry is corrected. There is a
test in this repo that fails if anyone adds one.

## Build a schedule

```python
sched = ShotScheduleBody(
    schedule_id="sch-001",
    title="Scene 4 — the pub",
    model_id="fal-ai/bytedance/seedance/v1/pro/image-to-video",  # a reference
    aspect="16:9",
    resolution="720p",
    shots=(
        ShotEntry(
            shot_id="sh-01",
            panel_id="p1",  # optional link to the realizing panel
            beat_id="b1",  # optional parent beat
            description="Mairead pushes the door open.",
            characters=("Mairead",),  # character-ref *names*
            shot_size="MS",
            angle="EYE_LEVEL",
            movement="LOCKED",
            duration_seconds_estimate=6.0,
            duration_source="estimate",
            # --- constraints a planner must respect ---
            max_duration_seconds=8.0,
            max_characters_in_frame=1,
            take_budget=3,
            clump_id="pub-interior",
        ),
    ),
)
```

`new_shot_id()` / `new_schedule_id()` give short fresh ids (`"sh3f7c1"`,
`"sch3f7c1"`) when nothing stable exists yet.

## Persist and load

```python
from artful import save_shot_schedule, load_shot_schedule, load_shot_schedules
from lacing import MemoryStore  # or SQLiteStore, PostgresStore, ...

store = MemoryStore()
save_shot_schedule(sched, store, asset_id="song-asset-id-abc")

loaded = load_shot_schedule(store, asset_id="song-asset-id-abc")
```

- `asset_id` goes on the annotation's reference, **not** into the body —
  same split as `PanelBody` and its interval.
- `save_shot_schedule` **appends**. Saving twice keeps both, so a store can
  hold a schedule's revision history. Tell them apart with `schedule_id`
  (`load_shot_schedule(..., schedule_id="v2")`) or with `tier`.
- `load_shot_schedules` (plural) returns every schedule for an asset/tier;
  `load_shot_schedule` (singular) returns one, or `None`.
- Default tier is `SHOT_SCHEDULE_TIER == "shot-schedule"`.

## Constraint fields, and the pitfall each one guards

Every constraint exists because a real tool fails without it. Set them
deliberately; the defaults are the safe choice, not the permissive one.

| field | guards against |
|---|---|
| `max_characters_in_frame` | Two people in one frame come back with merged faces / one stranger. Set `1` and stage it as shot/reverse-shot. |
| `max_duration_seconds` | A model's nominal cap is optimistic: complex shots (dialogue + action + more than one character) degrade *before* it. Tighten this **below** the model's `max_clip_seconds` for complex shots — that is exactly why it is separate from the model's cap. |
| `allow_last_frame_anchor` | Anchoring **both** a first and a last frame contorts the subject mid-clip. Defaults to `False`; opt in only for hard continuity cuts where the pose barely moves. |
| `aspect` | Relying on a platform's default aspect crops the subject out of frame. Set it explicitly per generation. |
| `resolution` | Max resolution multiplies cost and render time for marginal gain. Draft at the cheap tier; reserve the expensive one for locked hero shots. Must be one of the model's `supported_resolutions` — that list lives in falaw, not here. |
| `take_budget` | A regeneration costs full price. `None` means unbounded, which is a *decision* — state it deliberately. |
| `clump_id` | Free-form grouping key for shots that batch well (same model / setting / character), so a user fires one clump and works while it renders. |
| `has_dialogue` / `has_action` | The two signals an advisor needs to know a shot is "complex" and should be planned short. |

## Risk flags — a cached verdict, not a constraint

```python
RiskFlag(
    code="over_clip_cap",  # controlled vocabulary
    message="~14s is over this model's ~10s clip cap.",
    severity="warn",  # "warn" | "info"
    gotcha_id="seedance-clip-length-cap",  # into reelee's gotchas registry
)
```

`RiskCode` is a closed vocabulary: `over_clip_cap`, `multi_character`,
`first_last_frame`, `dialogue_plus_action`, `over_take_budget`,
`unsupported_resolution`, `mixed_aspect_ratios`. Adding one is an additive
schema change, made deliberately.

**`over_clip_cap` and `multi_character` are the exact strings reelee's shot
advisor emits as `ShotWarning.code`.** Never rename them — one code
vocabulary across the federation, not two. (artful cannot import reelee;
the dependency runs the other way, so a test pins the literal strings.)

Flags on a `ShotEntry` are about that shot. Flags on the
`ShotScheduleBody` are about the list as a whole (e.g.
`mixed_aspect_ratios`).

### Staleness — always check before trusting a flag

```python
if sched.needs_advice:
    ...  # re-run the advisor; the cached flags are for a different model
```

`needs_advice` is `True` when `model_id` is set and
`advised_for_model_id != model_id` — which covers both "never advised" and
"the model changed since". A schedule with no `model_id` cannot be advised,
so it never *needs* advice.

After advising, write both together:

```python
sched = sched.model_copy(
    update={
        "shots": advised_shots,
        "advised_for_model_id": sched.model_id,
    }
)
```

## Vocabulary is shared, not re-invented

When you touch this schema, reuse rather than mint:

- **Shot grammar** — `shot_size` / `angle` / `movement` are artful's own
  `ShotSize` / `Angle` / `Movement` literals, the same objects `PanelBody`
  uses. One taxonomy, two carriers.
- **Duration** — `duration_seconds_estimate` / `duration_source`, the
  names already on `PanelBody`. Not `est_duration_s`.
- **Characters** — named by their character-ref `name`, matching
  `PanelBody.moment_focal_character_ref`'s convention. Costume, palette
  and do-not-do directives live on the character-ref / model sheet; a
  schedule row *references* the character, it does not restate them.
- **Gotchas** — `RiskFlag.gotcha_id` points at the registry entry by id so
  the mitigation prose has exactly one home.

## Common gotchas

- **Order is tuple order.** There is deliberately no `order` field to
  disagree with the position in `shots`. Reordering means rebuilding the
  tuple.
- **Character count is `len(characters)`.** There is no `character_count`
  field, because that is what an advisor already computes and a second
  field would drift.
- **Frozen models, `extra="forbid"`.** Build new versions with
  `model_copy(update={...})`; an unknown field raises rather than being
  silently dropped.
- **The schedule is a plan, not a ledger.** `take_budget` is the bound;
  takes actually consumed are counted from render annotations, not stored
  here.
- **Plan vs realization.** When an entry names a `panel_id` / `shot_id`,
  those annotations are authoritative for the *realized* shot; the grammar
  fields on the entry are the *planned* values.

## Schema registration

Importing `artful` registers `ShotScheduleBody` under
`SHOT_SCHEDULE_BODY_SCHEMA_URI == "annot://schema/shot-schedule/v1"`, so
`lacing.validate_body(body, SHOT_SCHEDULE_BODY_SCHEMA_URI)` works, and any
JSON-Schema export that walks lacing's registry picks it up automatically
(with `ShotEntry` and `RiskFlag` as `$defs` for frontend codegen).
