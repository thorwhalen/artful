"""Storyboard schema — typed Panels along a timeline, lacing-native.

A *storyboard* is a sequence of *panels*. Each panel:

- Spans a time interval on a project's master timeline (song time, scene
  time, podcast clip time).
- Optionally points at a shot (or other unit) in the project graph.
- Carries one or more *image references* — generated stills, hand drawings,
  screenshots, or pointers to a `lacing.Artifact` in storage.
- Carries directorial annotations: caption, framing, camera, transition,
  notes.

Panels are persisted as :class:`lacing.Annotation` records with body schema
``annot://schema/storyboard-panel/v1``, registered into lacing on package
import. That means a storyboard is queryable, exportable, and round-trippable
through every adapter lacing already supports (TextGrid, EAF, JAMS, OTIO,
WebVTT, Web Annotation), with provenance tracked across edits.

A storyboard is **not** the rendered video — it's the panels-along-a-timeline
plan that drives the renderer. Use cases:

- A human draws or arranges panels; an agent renders the panel images via
  ``nw.render_storyboard_images``.
- An agent generates panels from a script; a human reviews them as a PDF.
- The same panel data populates both a printed contact sheet and the
  i2v / composite_lipsync seed images for downstream rendering.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from lacing import register_body_schema


ReviewStatus = Literal[
    "unreviewed",
    "approved",
    "needs-revision",
    "rejected",
]
"""Review status of a storyboard panel. Defaults to ``"unreviewed"``;
the FE Kanban view + per-panel review badge consume this. v0.3
persisted-review-status field — backward-compatible (existing dump
files without the field get the default)."""


MomentHeuristic = Literal[
    "decisive_composition",
    "apex_of_action",
    "just_before_recognition",
    "held_breath",
    "reaction_not_action",
    "entry_for_clip",
    "expression_over_action",
    "silhouette_test",
    "eyeline_contact",
]
"""Spec §7.2 iconic-frame heuristics. ``entry_for_clip`` is the
mandatory choice for ``ai_cinematic_clip`` output intents (where the
video model interpolates forward from the depicted frame)."""


MomentTiming = Literal["entry", "mid", "apex", "exit"]
"""Spec §7.2 — where in the implied motion the depicted frame sits."""


ShotSize = Literal[
    "ECU",
    "CU",
    "MCU",
    "MS",
    "MWS",
    "WS",
    "LS",
    "ELS",
    "INSERT",
    "TWO_SHOT",
    "THREE_SHOT",
    "GROUP",
    "MASTER",
]
"""Spec §6.3 shot-size taxonomy. Controlled vocabulary — distinct from the
free-text :attr:`PanelBody.framing` field. This is the single source of truth
for the storyboard-panel schema; ``reelee.bodies.shot`` re-exports these so the
shot-grammar advisor and the panel body share one vocabulary."""


Angle = Literal[
    "EYE_LEVEL",
    "HIGH",
    "LOW",
    "DUTCH",
    "BIRDS_EYE",
    "WORMS_EYE",
    "PROFILE",
    "THREE_QUARTER",
    "OTS",
    "POV",
]
"""Spec §6.3 / §9.3 angle taxonomy. Controlled vocabulary — distinct from the
free-text :attr:`PanelBody.camera` field."""


Movement = Literal[
    "LOCKED",
    "PAN",
    "TILT",
    "DOLLY_IN",
    "DOLLY_OUT",
    "TRUCK",
    "PEDESTAL",
    "ZOOM",
    "CRANE",
    "HANDHELD",
    "WHIP_PAN",
    "DOLLY_ZOOM",
]
"""Spec §6.3 movement taxonomy. ``LOCKED`` is the default in practice."""


DurationSource = Literal["estimate", "from_voiceover", "from_clip", "manual"]
"""Spec §7.5 — provenance of a panel's duration field. ``manual``
indicates the user overrode the estimate."""


# Body-schema URI for storyboard panels. Versioned (v1).
PANEL_BODY_SCHEMA_URI = "annot://schema/storyboard-panel/v1"


class PanelImage(BaseModel):
    """One image associated with a panel.

    Either an ``artifact_id`` (pointing into lacing's Artifact registry by
    content hash) or a direct ``url`` / ``path`` is required. ``role``
    distinguishes "this is the thumbnail you show on the contact sheet"
    from "this is the seed image for the renderer."
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: Optional[str] = Field(
        None,
        description=(
            "SHA-256 content hash of the image bytes (matches "
            "`lacing.Artifact.asset_id`). Preferred over `url` / `path` for "
            "cross-machine identity."
        ),
    )
    url: Optional[str] = Field(None, description="Remote URL, if applicable.")
    path: Optional[str] = Field(
        None, description="Local filesystem path, project-relative when possible."
    )
    role: str = Field(
        "thumbnail",
        description=(
            'One of: "thumbnail" (default — what to show in contact sheet), '
            '"seed" (image that drives the downstream renderer), '
            '"reference" (input the panel was generated from), '
            '"alternate" (variant a curator can pick from).'
        ),
    )
    caption: str = ""


class PanelBody(BaseModel):
    """The body of a storyboard-panel annotation.

    Persisted as the ``body`` dict of a :class:`lacing.Annotation` whose
    ``body_schema_uri`` is :data:`PANEL_BODY_SCHEMA_URI`.

    The annotation's ``reference`` (a :class:`lacing.MediaRef`) carries the
    interval — i.e. the time span this panel covers — so we don't duplicate
    interval information here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    panel_id: str = Field(
        ...,
        description="Stable id within a storyboard. Distinct from the annotation id.",
    )
    shot_id: Optional[str] = Field(
        None,
        description=(
            "Optional pointer to a project shot (e.g. nw.ShotSpec.id). "
            "When set, the panel illustrates that shot."
        ),
    )
    images: tuple[PanelImage, ...] = Field(
        default_factory=tuple,
        description="One or more images for this panel.",
    )
    caption: str = Field(
        "", description="Free-form description shown beside the panel."
    )
    framing: str = Field(
        "",
        description=(
            'Camera framing. Common values: "wide", "medium", "close", '
            '"ecu" (extreme close-up), "insert", "ots" (over-the-shoulder).'
        ),
    )
    camera: str = Field(
        "", description='Camera move: "static", "slow push-in", "pan-left", etc.'
    )
    transition_in: str = Field(
        "cut",
        description='Transition into this panel: "cut" | "fade" | "match-cut" | …',
    )
    notes: str = Field(
        "", description="Director's notes; not shown on the contact sheet."
    )
    review_status: ReviewStatus = Field(
        "unreviewed",
        description=(
            "Per-panel review status. Cycles through unreviewed → "
            "approved → needs-revision → rejected via the FE's "
            "panel.review.cycle command. Defaults to 'unreviewed' so "
            "v0.2-era dump files (which don't carry this field) load "
            "cleanly."
        ),
    )
    active_image_index: int = Field(
        0,
        description=(
            "Index into ``images`` of the currently-active alternate — "
            "the one the picture-book / gallery / kanban renders. "
            "Multiple images in ``images`` are treated as alternates "
            "(generated variations of the same shot); this field "
            "tracks which one the director has chosen. Defaults to 0 "
            "so a single-image panel always renders that one image, "
            "and v0.3-era dump files (no field) round-trip cleanly."
        ),
        ge=0,
    )
    # --- Narrative→Storyboard (Phase 0) additive fields ---------------
    # All Optional, all None-default — pre-Phase-0 dump files load cleanly.
    moment_caption: Optional[str] = Field(
        None,
        description=(
            "One-line gloss of the depicted moment (spec §7.2). Distinct "
            "from ``caption``: caption is the user-facing line; "
            "moment_caption is the segmenter's choice rationale."
        ),
    )
    moment_heuristic: Optional[MomentHeuristic] = Field(
        None, description="Which iconic-frame heuristic picked this moment (spec §7.2)."
    )
    moment_timing: Optional[MomentTiming] = Field(
        None,
        description=(
            "entry / mid / apex / exit — where in the implied motion the "
            "depicted frame sits. Drives ``ai_cinematic_clip`` rendering."
        ),
    )
    moment_focal_character_ref: Optional[str] = Field(
        None,
        description=(
            "Name of the focal character-ref for this panel (multi-char "
            "beats; spec §7.2 priority rule)."
        ),
    )
    split_from_beat_id: Optional[str] = Field(
        None,
        description=(
            "If this panel was produced by splitting one beat into N "
            "panels, the beat id. Spec §7.1 PanelExtensionSplitProvenance."
        ),
    )
    split_index: Optional[int] = Field(
        None, description="0-based index of this panel within its beat split."
    )
    split_total: Optional[int] = Field(
        None, description="Total panels produced from the beat split."
    )
    split_reason: Optional[str] = Field(
        None,
        description=(
            '"verb-clause" | "shot-reverse-shot" | "just-before/after" | '
            '"montage" | … (spec §7.1).'
        ),
    )
    # --- Shot grammar (spec §6.3) — controlled vocabulary -------------
    # Distinct from the free-text ``framing`` / ``camera`` fields above.
    # Set deterministically by the shot-grammar advisor (reelee §6.3 rule
    # table) and read by the prompt builder's ``shot_size`` / ``angle``
    # slots. All Optional / None-default — additive, no migration needed.
    shot_size: Optional[ShotSize] = Field(
        None,
        description=(
            "Controlled shot-size taxonomy value (spec §6.3): ECU/CU/MCU/"
            "MS/MWS/WS/LS/ELS/INSERT/TWO_SHOT/THREE_SHOT/GROUP/MASTER. "
            "Set by the shot-grammar advisor from the beat's semantic tag "
            "and action line; consumed by ``panel_to_prompt`` for a stable "
            "``shot_size`` slot. Distinct from the free-text ``framing``."
        ),
    )
    angle: Optional[Angle] = Field(
        None,
        description=(
            "Controlled angle taxonomy value (spec §6.3): EYE_LEVEL/HIGH/"
            "LOW/DUTCH/BIRDS_EYE/WORMS_EYE/PROFILE/THREE_QUARTER/OTS/POV. "
            "Distinct from the free-text ``camera`` field."
        ),
    )
    movement: Optional[Movement] = Field(
        None,
        description=(
            "Controlled camera-movement taxonomy value (spec §6.3): LOCKED/"
            "PAN/TILT/DOLLY_IN/DOLLY_OUT/TRUCK/PEDESTAL/ZOOM/CRANE/HANDHELD/"
            "WHIP_PAN/DOLLY_ZOOM. ``LOCKED`` is the practical default for "
            "static boards; AI-cinematic intents read it for motion prompts."
        ),
    )
    duration_seconds_estimate: Optional[float] = Field(
        None,
        description=(
            "Estimated panel duration in seconds (spec §7.5). Float here "
            "is intentional — RationalTime is materialized only when the "
            "panel commits to a timeline. See PanelDurationExtension."
        ),
        ge=0.0,
    )
    duration_source: Optional[DurationSource] = Field(
        None,
        description=(
            "Where the duration value came from. ``manual`` indicates "
            "user override of the estimate."
        ),
    )
    duration_confidence: Optional[float] = Field(
        None,
        description="0..1 confidence on the duration estimate.",
        ge=0.0,
        le=1.0,
    )
    duration_model_version: Optional[str] = Field(
        None,
        description=(
            "Version of the duration model that produced the estimate, "
            "for cache-busting when the model changes."
        ),
    )


class Storyboard(BaseModel):
    """A typed view over a sequence of panel annotations.

    Storyboards are *constructed* from in-memory data and *persisted* by
    writing each panel as a lacing :class:`Annotation`. Use the helpers in
    :mod:`artful.store` to round-trip with a lacing store.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = ""
    asset_id: str = Field(
        ...,
        description=(
            "The asset_id of the timeline this storyboard is plotted on "
            "(typically the song / video the panels reference)."
        ),
    )
    panels: tuple[PanelBody, ...] = Field(default_factory=tuple)
    style: str = Field("", description="Global visual-style hint for image gen.")
    aspect: str = Field("16:9", description='Aspect ratio: "16:9" | "9:16" | "1:1" | …')

    def panel(self, panel_id: str) -> Optional[PanelBody]:
        for p in self.panels:
            if p.panel_id == panel_id:
                return p
        return None


def new_panel_id(prefix: str = "p") -> str:
    """Generate a fresh short panel id (e.g. ``"p3f7c1"``)."""
    return f"{prefix}{_uuid.uuid4().hex[:6]}"


# --- Model sheet -----------------------------------------------------------

# Body-schema URI for character model sheets (spec §7.4).
MODEL_SHEET_BODY_SCHEMA_URI = "annot://schema/model-sheet/v1"


ModelSheetView = Literal[
    "front",
    "three_quarter_front",
    "side_left",
    "side_right",
    "three_quarter_back",
    "back",
]
"""Canonical model-sheet views (spec §7.4 conventions)."""


class ModelSheet(BaseModel):
    """The body of a model-sheet annotation — a character's canonical
    turnaround, expression set, and supporting metadata.

    Produced by ``character_to_modelsheet.<flavor>.<model>`` (spec §7.4).
    Lives in artful (next to PanelBody) because it is a storyboard-adjacent
    asset: model sheets feed into per-panel renders as reference images,
    and the inspector surfaces them alongside the panels they conditioned.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    character_ref_id: str = Field(
        ...,
        description=(
            "Id of the character-ref this sheet belongs to (the schema "
            "for character-ref/v1 lives in nw)."
        ),
    )
    sheet_id: str = Field(
        ..., description="Stable id within the project (e.g. 'ms-001')."
    )
    canonical_views: dict[ModelSheetView, str] = Field(
        default_factory=dict,
        description=(
            "Map of canonical view → ``render-result`` annotation id. Not "
            "every view is required for v1; the producing Transform fills "
            "the views it can hit."
        ),
    )
    expression_set: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of expression label (e.g. 'joy', 'fear', 'neutral') → "
            "``render-result`` annotation id."
        ),
    )
    costume_set: dict[str, str] = Field(
        default_factory=dict,
        description="Map of costume label → ``render-result`` annotation id.",
    )
    palette_anchors: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Hex color anchors for this character.",
    )
    distinguishing_features: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            'Free-text feature notes — "left eye scar", "red bandana". '
            "Appended to character_ref prompt slots."
        ),
    )
    head_to_body_ratio: Optional[float] = Field(
        None,
        description=(
            "Conventional 7.5 for realistic, 5-6 for anime/cutout, 2-3 "
            "for chibi, 4-5 for children's book. None lets the flavor "
            "decide."
        ),
        gt=0.0,
    )
    do_not_do: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Negative-prompt directives, character-scoped (spec §7.4).",
    )
    age_progression: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of age label (e.g. 'child', 'elder') → ``render-result`` "
            "annotation id. Optional."
        ),
    )
    prop_interactions: dict[str, str] = Field(
        default_factory=dict,
        description="Map of prop id → ``render-result`` annotation id.",
    )
    voice_personality_notes: Optional[str] = Field(
        None,
        description="Free-text personality notes for downstream LLM/TTS.",
    )


# --- lacing body-schema registration ---------------------------------------
# Importing this module registers the panel body schema with lacing's global
# registry, so any annotation with body_schema_uri=PANEL_BODY_SCHEMA_URI is
# validated against PanelBody.

register_body_schema(PANEL_BODY_SCHEMA_URI, PanelBody)
register_body_schema(MODEL_SHEET_BODY_SCHEMA_URI, ModelSheet)
