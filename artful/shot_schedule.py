"""Shot schedule — an ordered, model-constraint-aware shot list.

A *shot schedule* is the planning document that sits between a scene
breakdown and a storyboard: an ordered list of shots, each carrying the
constraints a downstream planner must respect (clip-length cap, how many
characters may share the frame, aspect / resolution, how many takes the
shot is allowed to burn) plus the advisory *risk flags* raised when those
constraints collide with the chosen video model's real limits.

Persisted as a **single** :class:`lacing.Annotation` with body schema
``annot://schema/shot-schedule/v1``. One annotation, not one per shot,
because a schedule exists *before* times are pinned — the ordering is the
tuple order of :attr:`ShotScheduleBody.shots`, not an interval sort.

Three sources of truth, deliberately kept apart
-----------------------------------------------

============================  =========================================
what                          who owns it
============================  =========================================
what a *model* can do         ``falaw``'s model registry
                              (``max_clip_seconds``,
                              ``single_character_recommended``,
                              ``supported_resolutions``, …). Referenced
                              here by :attr:`ShotScheduleBody.model_id`
                              — **never copied**.
what a *shot* requires        this schema (``max_duration_seconds``,
                              ``max_characters_in_frame``, ``aspect``,
                              ``resolution``, ``take_budget``).
what happens when they        :class:`RiskFlag` — the cached verdict of
collide                       comparing the two. Computed by reelee's
                              shot advisor; stamped with
                              :attr:`ShotScheduleBody.advised_for_model_id`
                              so a model change makes the flags visibly
                              stale (:attr:`ShotScheduleBody.needs_advice`).
============================  =========================================

Vocabulary is shared, not re-invented: shot grammar (``shot_size`` /
``angle`` / ``movement``) reuses the controlled taxonomies defined in
:mod:`artful.schema`; ``duration_seconds_estimate`` / ``duration_source``
reuse the names already on :class:`artful.PanelBody`; characters are named
by their ``character-ref`` name (the schema for ``character-ref/v1`` lives
in ``nw``), matching :attr:`artful.PanelBody.moment_focal_character_ref`;
and :attr:`RiskFlag.gotcha_id` points into reelee's tool-gotchas registry
rather than restating the mitigation prose here.

Plan vs realization: when a shot entry names a ``panel_id`` / ``shot_id``,
those annotations are authoritative for the *realized* shot. The grammar
fields here are the *planned* values — what the schedule intends before a
panel exists.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Iterable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from lacing import (
    Annotation,
    IntervalAnnotationStore,
    MediaRef,
    TimeInterval,
    register_body_schema,
)

from .schema import Angle, DurationSource, Movement, ShotSize
from .store import make_prov


# Body-schema URI for shot schedules. Versioned (v1).
SHOT_SCHEDULE_BODY_SCHEMA_URI = "annot://schema/shot-schedule/v1"

SHOT_SCHEDULE_TIER = "shot-schedule"
"""Default lacing tier for persisted schedules — so several schedules over
one asset (a draft and a revision, say) stay distinguishable by tier."""


RiskCode = Literal[
    "over_clip_cap",
    "multi_character",
    "first_last_frame",
    "dialogue_plus_action",
    "over_take_budget",
    "unsupported_resolution",
    "mixed_aspect_ratios",
]
"""Controlled vocabulary of advisory flags a shot advisor may raise.

``over_clip_cap`` and ``multi_character`` are **the same strings** the
reelee shot advisor already emits as ``ShotWarning.code``; do not rename
them — one code vocabulary across the federation, not two. The rest name
pitfalls that are already curated entries in reelee's tool-gotchas
registry (``seedance-first-last-frame-contortion``,
``seedance-dialogue-plus-action-degrades``, ``regen-full-price``,
``resolution-cost-tradeoff``, ``aspect-ratio-crop-surprise``).

Closed vocabulary, per artful convention: adding a code is an additive
schema change, made deliberately.
"""


RiskSeverity = Literal["info", "warn"]
"""Matches the reelee shot advisor's ``ShotWarning.severity`` exactly."""


class RiskFlag(BaseModel):
    """One advisory warning attached to a shot (or to the whole schedule).

    A *cached verdict*, not a constraint: it records that this shot's
    requirements collided with the limits of the model named by
    :attr:`ShotScheduleBody.advised_for_model_id`. Re-advise after
    changing the model — :attr:`ShotScheduleBody.needs_advice` says when.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: RiskCode = Field(..., description="Controlled advisory code.")
    message: str = Field(
        "", description="Human-readable explanation, as the advisor worded it."
    )
    severity: RiskSeverity = Field(
        "warn", description='"warn" (act on it) or "info" (be aware).'
    )
    gotcha_id: Optional[str] = Field(
        None,
        description=(
            "Id of the entry in reelee's tool-gotchas registry that explains "
            "this pitfall (e.g. 'seedance-clip-length-cap'). Referenced by "
            "id so the mitigation prose has exactly one home."
        ),
    )


class ShotEntry(BaseModel):
    """One row of a shot schedule: what to shoot, and what bounds it.

    Position in :attr:`ShotScheduleBody.shots` **is** the shot's order —
    there is deliberately no ``order`` field to disagree with it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shot_id: str = Field(
        ...,
        description=(
            "Stable id within the schedule (e.g. 'sh-014'). When a "
            "``shot/v1`` annotation exists for this shot, use its "
            "``shot_id`` so the two line up."
        ),
    )
    panel_id: Optional[str] = Field(
        None,
        description=(
            "Optional pointer to the storyboard panel realizing this shot "
            "(``PanelBody.panel_id``). When set, the panel is authoritative "
            "for the realized grammar; the fields below are the plan."
        ),
    )
    beat_id: Optional[str] = Field(
        None, description="Optional parent beat id (``beat/v1``)."
    )
    description: str = Field(
        "", description="Free-text directorial description of this shot."
    )
    characters: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Names of the character-refs in frame (``character-ref/v1`` "
            "``name``), matching PanelBody.moment_focal_character_ref's "
            "convention of naming rather than embedding. The character "
            "*count* an advisor checks is ``len(characters)`` — there is no "
            "separate count field to drift from it."
        ),
    )

    # --- planned shot grammar (controlled vocabulary, shared with PanelBody)
    shot_size: Optional[ShotSize] = Field(
        None, description="Planned shot-size taxonomy value (spec §6.3)."
    )
    angle: Optional[Angle] = Field(
        None, description="Planned angle taxonomy value (spec §6.3)."
    )
    movement: Optional[Movement] = Field(
        None, description="Planned camera-movement taxonomy value (spec §6.3)."
    )

    # --- planned duration (same field names as PanelBody) ------------------
    duration_seconds_estimate: Optional[float] = Field(
        None,
        description=(
            "Estimated shot duration in seconds. Same name and meaning as "
            "``PanelBody.duration_seconds_estimate`` — float here is "
            "intentional; RationalTime is materialized only once the shot "
            "commits to a timeline."
        ),
        ge=0.0,
    )
    duration_source: Optional[DurationSource] = Field(
        None, description="Where the duration estimate came from."
    )

    # --- constraints a downstream planner must respect ---------------------
    max_duration_seconds: Optional[float] = Field(
        None,
        description=(
            "Hard upper bound for this shot, in seconds. Distinct from the "
            "estimate: the estimate is what we think it will be, this is "
            "what it may not exceed. Typically tightened below the model's "
            "``max_clip_seconds`` for complex shots (dialogue + action + "
            "more than one character degrade before the nominal cap)."
        ),
        gt=0.0,
    )
    max_characters_in_frame: Optional[int] = Field(
        None,
        description=(
            "Hard upper bound on characters sharing the frame. Set to 1 to "
            "enforce the single-character rule on a model that needs it "
            "(gotcha 'single-character-per-frame'); the fix is "
            "shot/reverse-shot, not a bigger number."
        ),
        ge=1,
    )
    aspect: Optional[str] = Field(
        None,
        description=(
            'Per-shot aspect override ("16:9" | "9:16" | "1:1" | …). None '
            "inherits ``ShotScheduleBody.aspect``. Explicit per generation, "
            "because relying on a platform default is what crops the "
            "subject out of frame (gotcha 'aspect-ratio-crop-surprise')."
        ),
    )
    resolution: Optional[str] = Field(
        None,
        description=(
            'Per-shot resolution override ("720p" | "1080p" | …), which must '
            "be one of the target model's ``supported_resolutions`` — that "
            "list lives in falaw and is not copied here. None inherits "
            "``ShotScheduleBody.resolution``."
        ),
    )
    allow_last_frame_anchor: bool = Field(
        False,
        description=(
            "Whether this shot may anchor BOTH a first and a last frame. "
            "Defaults to False because anchoring both contorts the subject "
            "mid-clip (gotcha 'seedance-first-last-frame-contortion'); opt "
            "in only for hard continuity cuts where the pose barely moves."
        ),
    )
    has_dialogue: bool = Field(
        False, description="Whether a character speaks on-camera in this shot."
    )
    has_action: bool = Field(
        False, description="Whether significant physical action occurs in this shot."
    )
    take_budget: Optional[int] = Field(
        None,
        description=(
            "Maximum generation attempts this shot is allowed to spend. "
            "A regeneration costs full price, so the budget is a planning "
            "constraint, not a hint (gotcha 'regen-full-price'). None means "
            "unbounded — which is a decision, so state it deliberately. "
            "Takes actually consumed are counted from render annotations; "
            "this body stays a plan, not a ledger."
        ),
        ge=1,
    )
    clump_id: Optional[str] = Field(
        None,
        description=(
            "Optional grouping key for shots that batch well together "
            "(same model, setting, or character), so a user can fire one "
            "clump and keep working while it renders. Free-form; the "
            "schedule does not enforce clump membership."
        ),
    )
    risk_flags: tuple[RiskFlag, ...] = Field(
        default_factory=tuple,
        description="Advisory flags raised for this shot. See RiskFlag.",
    )
    notes: str = Field("", description="Free-text planning notes.")


class ShotScheduleBody(BaseModel):
    """The body of a shot-schedule annotation — the ordered shot list.

    The annotation's ``reference`` carries the ``asset_id`` this schedule
    plans, so it is not duplicated here (same split as
    :class:`artful.PanelBody`).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schedule_id: str = Field(
        ..., description="Stable id within the project (e.g. 'sch-001')."
    )
    title: str = Field("", description="Human-readable name for this schedule.")
    model_id: Optional[str] = Field(
        None,
        description=(
            "The video model this schedule is planned against, as a falaw "
            "model id or alias. A *reference*: every limit value "
            "(``max_clip_seconds``, ``single_character_recommended``, "
            "``supported_resolutions``, …) is looked up in falaw's registry, "
            "never copied into this body, so a registry correction cannot "
            "leave a stale duplicate behind."
        ),
    )
    advised_for_model_id: Optional[str] = Field(
        None,
        description=(
            "The model id the current ``risk_flags`` were computed against. "
            "When it differs from ``model_id`` the flags are stale — see "
            "``needs_advice``."
        ),
    )
    aspect: str = Field(
        "16:9",
        description=(
            'Schedule-wide aspect ratio ("16:9" | "9:16" | "1:1" | …). '
            "Individual shots may override it via ``ShotEntry.aspect``."
        ),
    )
    resolution: Optional[str] = Field(
        None,
        description=(
            "Schedule-wide default resolution, overridable per shot. None "
            "leaves the choice to the renderer."
        ),
    )
    shots: tuple[ShotEntry, ...] = Field(
        default_factory=tuple,
        description="The shots, in shooting order. Tuple order is the order.",
    )
    risk_flags: tuple[RiskFlag, ...] = Field(
        default_factory=tuple,
        description=(
            "Schedule-wide advisory flags — the ones that are a property of "
            "the list rather than of any single shot (e.g. "
            "``mixed_aspect_ratios``)."
        ),
    )
    notes: str = Field("", description="Free-text planning notes.")

    def shot(self, shot_id: str) -> Optional[ShotEntry]:
        """The entry with ``shot_id``, or None. Mirrors ``Storyboard.panel``."""
        for s in self.shots:
            if s.shot_id == shot_id:
                return s
        return None

    @property
    def needs_advice(self) -> bool:
        """True when the risk flags do not (or no longer) match ``model_id``.

        A schedule with no ``model_id`` cannot be advised, so it never
        *needs* advice; one whose model changed since it was advised always
        does.
        """
        if self.model_id is None:
            return False
        return self.advised_for_model_id != self.model_id


def new_shot_id(prefix: str = "sh") -> str:
    """Generate a fresh short shot id (e.g. ``"sh3f7c1"``)."""
    return f"{prefix}{_uuid.uuid4().hex[:6]}"


def new_schedule_id(prefix: str = "sch") -> str:
    """Generate a fresh short schedule id (e.g. ``"sch3f7c1"``)."""
    return f"{prefix}{_uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# Store round-trip
# ---------------------------------------------------------------------------


def save_shot_schedule(
    schedule: ShotScheduleBody,
    store: IntervalAnnotationStore,
    *,
    asset_id: str,
    tier: str = SHOT_SCHEDULE_TIER,
    was_attributed_to: str = "user:unknown",
    was_generated_by: str = "agent:artful",
) -> Annotation:
    """Persist ``schedule`` into ``store`` as one timeless annotation.

    Like :func:`artful.save_storyboard` this *appends* — saving twice adds
    a second annotation rather than replacing the first, so a store can
    hold a schedule's revision history. Use ``tier`` (or ``schedule_id``)
    to tell revisions apart on load.

    Args:
        schedule: The :class:`ShotScheduleBody` to persist.
        store: Any :class:`lacing.IntervalAnnotationStore`.
        asset_id: The asset this schedule plans (goes on the annotation's
            ``reference``, not into the body).
        tier: Tier name for the persisted annotation.
        was_attributed_to / was_generated_by: Provenance fields.

    Returns:
        The persisted :class:`lacing.Annotation`.
    """
    ann = Annotation(
        id=_uuid.uuid4(),
        tier=tier,
        # A schedule spans no interval — it is the plan that decides the
        # intervals. Zero-duration placeholder, same as the storyboard-meta
        # record in artful.store.
        reference=MediaRef(asset_id=asset_id, interval=TimeInterval.from_seconds(0, 0)),
        body=schedule.model_dump(),
        body_schema_uri=SHOT_SCHEDULE_BODY_SCHEMA_URI,
        provenance=make_prov(was_generated_by, was_attributed_to),
    )
    store.add(ann)
    return ann


def load_shot_schedules(
    store: IntervalAnnotationStore,
    *,
    asset_id: str,
    tier: str = SHOT_SCHEDULE_TIER,
) -> list[ShotScheduleBody]:
    """Every schedule in ``store`` for ``asset_id`` / ``tier``, in store order."""
    return list(_iter_schedules(store, asset_id=asset_id, tier=tier))


def load_shot_schedule(
    store: IntervalAnnotationStore,
    *,
    asset_id: str,
    schedule_id: Optional[str] = None,
    tier: str = SHOT_SCHEDULE_TIER,
) -> Optional[ShotScheduleBody]:
    """One schedule, or None when there is no match.

    With ``schedule_id`` given, returns that schedule. Without it, returns
    the first schedule found for ``asset_id`` / ``tier`` — convenient for
    the common one-schedule-per-asset case.
    """
    for sched in _iter_schedules(store, asset_id=asset_id, tier=tier):
        if schedule_id is None or sched.schedule_id == schedule_id:
            return sched
    return None


def _iter_schedules(
    store: IntervalAnnotationStore, *, asset_id: str, tier: str
) -> Iterable[ShotScheduleBody]:
    for ann in store.all():
        if ann.tier != tier:
            continue
        if ann.body_schema_uri != SHOT_SCHEDULE_BODY_SCHEMA_URI:
            continue
        if not isinstance(ann.reference, MediaRef):
            continue
        if ann.reference.asset_id != asset_id:
            continue
        yield ShotScheduleBody.model_validate(ann.body)


# --- lacing body-schema registration ---------------------------------------

register_body_schema(SHOT_SCHEDULE_BODY_SCHEMA_URI, ShotScheduleBody)
