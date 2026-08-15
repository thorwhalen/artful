# artful — agent entry point

`artful` is the **storyboard data model** of the video_gen federation: panels
pinned to intervals of a master timeline and persisted as `lacing` annotations,
plus two storyboard-adjacent bodies (`ModelSheet`, `ShotScheduleBody`) and the
Markdown / HTML exporters. Five modules, no renderer, no storage of its own —
it is the shared storyboard *vocabulary* that `reelee`'s transforms and
`nw.storyboard` are built on. Small package, large blast radius.

## Blast radius — who reads this package

Verified by grepping the sibling repos; `nw` and `reelee` are the **only**
importers in the whole projects tree.

| Consumer | What it depends on |
|---|---|
| `nw/storyboard.py` | `Storyboard`, `PanelBody`, `PanelImage`, `save_storyboard` / `load_storyboard` / `panel_intervals_from_panels`; re-exports `to_html` / `to_markdown` / `from_markdown` |
| `nw/bodies/character_ref.py` + `nw/tests/test_bodies.py` | field names *and* types aligned to `ModelSheet` (`palette_anchors`, `distinguishing_features`, `do_not_do`) — nw has a test that fails if they drift |
| `reelee/transforms/beat_to_panel/` | `draft.py` builds `PanelBody` skeletons and declares `output_kind = PANEL_BODY_SCHEMA_URI`; `_shot_grammar.py` returns `ShotSize` / `Angle` / `Movement` values |
| `reelee/bodies/panel_draft.py`, `reelee/bodies/shot.py` | re-export artful's shot-grammar taxonomies — artful is the SSOT for `ShotSize` / `Angle` / `Movement` / `MomentHeuristic` / `MomentTiming` |
| `reelee/transforms/` (panel_to_image, panel_to_prompt, panel_alternates, panel_to_duration, panel_to_clip, panel_to_narration, panel_to_voiceover, paginate, continuity, environment_to_ambient, style_decision) | read and write panel annotations by URI |
| `reelee/transforms/character_to_modelsheet/cinematic.py` | writes `ModelSheet` bodies |
| `reelee/` app layer — `characters.py`, `agent.py`, `edits.py`, `storyboard_export.py`, `server.py`, `mcp/server.py`, `orchestrator/{consistency,supervisor,cost_estimate}.py` | query the project graph by panel / model-sheet URI |
| `reelee/genres.py` | **hardcodes** the panel URI as a string literal instead of importing it — a URI change here fails *silently* there, not at import |

## THE MIGRATION-REQUIRED RULE

artful owns four body-schema URIs:

    annot://schema/storyboard-panel/v1   PanelBody           (+ PanelImage)
    annot://schema/shot-schedule/v1      ShotScheduleBody    (+ ShotEntry, RiskFlag)
    annot://schema/model-sheet/v1        ModelSheet
    annot://schema/storyboard-meta/v1    StoryboardMetaBody

**These are the federation's carve-out from "clean shape over backward
compatibility".** Everywhere else in these repos, renaming for clarity in one
pass is the right move. Not here: annotations carrying these URIs are already
serialized in real user projects — `nw.storyboard` writes each project's
`storyboard.annot.sqlite`, reelee's server and MCP surface read them back, and
deployed instances hold data you cannot see from this repo. Changing a URI, or
renaming / removing / retyping / re-defaulting a serialized field, is a
**federation event** — it needs a new schema version plus a
`lacing.register_migration` from the old one, landed together with the
downstream updates. Adding an **optional** field with a default is additive and
needs no migration; that is how every field past v0.2 arrived.

`tests/test_body_schema_stability.py` pins the four URIs and every field's
serialized shape, and fails additive vs. breaking changes in separate tests
with different advice. If you are reading this because that test failed, the
paragraph above is the rule it is enforcing.

One nuance, true as of this writing: `shot-schedule/v1` has **no writer
anywhere in the federation yet** (`rg ShotSchedule` in reelee finds nothing),
so it alone still has no stored data behind it. It is the one body that is
still cheap to reshape — until reelee wires it, at which point it joins the
other three.

## Skills in this repo

- **artful** — building, persisting and loading storyboards. Load when working
  with `Storyboard` / `PanelBody` / `PanelImage` or a lacing round-trip.
- **artful-markdown** — the Markdown round-trip format. Load when an LLM or a
  human authors or edits panels as text (`to_markdown` / `from_markdown`).
- **artful-shot-schedule** — the `shot-schedule/v1` planning body. Load when
  planning shots against a video model's real limits, before panels exist.

## House rules

- Every *body* model is frozen with `extra="forbid"`; build new versions with
  `model_copy(update=…)`. `Storyboard` — the in-memory view, never a body — is
  the one mutable model.
- Intervals live on the lacing annotation's `reference`, never in a body.
- Model limits (`max_clip_seconds`, `supported_resolutions`, …) live in `falaw`
  and are referenced by `model_id`, never copied into a body.
- artful must not import `reelee` or `nw` — the dependency runs the other way.
  Shared vocabulary is pinned by literal in tests instead.
- `pytest` from the repo root: 75 tests, fully offline, no network, no cost.
