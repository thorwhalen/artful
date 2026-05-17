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


# --- lacing body-schema registration ---------------------------------------
# Importing this module registers the panel body schema with lacing's global
# registry, so any annotation with body_schema_uri=PANEL_BODY_SCHEMA_URI is
# validated against PanelBody.

register_body_schema(PANEL_BODY_SCHEMA_URI, PanelBody)
