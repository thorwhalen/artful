"""artful — Storyboard data model and exporters.

A *storyboard* is a sequence of *panels* along a timeline. Each panel pins
an interval of the master asset (a song, video, podcast clip), optionally
points at a project shot, and carries one or more images plus directorial
annotations.

Panels are persisted as :class:`lacing.Annotation` records with body schema
``annot://schema/storyboard-panel/v1``. That means a storyboard is queryable
with lacing's full toolkit (Allen interval algebra, store backends, format
adapters) without artful having to reinvent any of it.

Alongside the storyboard, artful owns two storyboard-adjacent bodies:
:class:`ModelSheet` (a character's canonical turnaround) and
:class:`ShotScheduleBody` (the ordered, model-constraint-aware shot list
that precedes the panels — see :mod:`artful.shot_schedule`).

Public surface:

- :class:`Storyboard`, :class:`PanelBody`, :class:`PanelImage` — Pydantic
  models for in-memory work.
- :func:`save_storyboard` / :func:`load_storyboard` — round-trip with any
  :class:`lacing.IntervalAnnotationStore`.
- :func:`to_markdown` / :func:`from_markdown` — round-trip Markdown
  (the canonical format for LLM authoring).
- :func:`to_html` — self-contained HTML contact sheet for review.
- :class:`ShotScheduleBody`, :class:`ShotEntry`, :class:`RiskFlag` +
  :func:`save_shot_schedule` / :func:`load_shot_schedule` — the shot
  schedule and its store round-trip.
"""

from .exports import from_markdown, to_html, to_markdown
from .schema import (
    MODEL_SHEET_BODY_SCHEMA_URI,
    PANEL_BODY_SCHEMA_URI,
    Angle,
    DurationSource,
    ModelSheet,
    ModelSheetView,
    MomentHeuristic,
    MomentTiming,
    Movement,
    PanelBody,
    PanelImage,
    ShotSize,
    Storyboard,
    new_panel_id,
)
from .shot_schedule import (
    SHOT_SCHEDULE_BODY_SCHEMA_URI,
    SHOT_SCHEDULE_TIER,
    RiskCode,
    RiskFlag,
    RiskSeverity,
    ShotEntry,
    ShotScheduleBody,
    load_shot_schedule,
    load_shot_schedules,
    new_schedule_id,
    new_shot_id,
    save_shot_schedule,
)
from .store import (
    STORYBOARD_META_BODY_SCHEMA_URI,
    StoryboardMetaBody,
    load_storyboard,
    panel_intervals_from_panels,
    save_storyboard,
)

__all__ = [
    "MODEL_SHEET_BODY_SCHEMA_URI",
    "PANEL_BODY_SCHEMA_URI",
    "SHOT_SCHEDULE_BODY_SCHEMA_URI",
    "SHOT_SCHEDULE_TIER",
    "STORYBOARD_META_BODY_SCHEMA_URI",
    "Angle",
    "DurationSource",
    "ModelSheet",
    "ModelSheetView",
    "MomentHeuristic",
    "MomentTiming",
    "Movement",
    "PanelBody",
    "PanelImage",
    "RiskCode",
    "RiskFlag",
    "RiskSeverity",
    "ShotEntry",
    "ShotScheduleBody",
    "ShotSize",
    "Storyboard",
    "StoryboardMetaBody",
    "from_markdown",
    "load_shot_schedule",
    "load_shot_schedules",
    "load_storyboard",
    "new_panel_id",
    "new_schedule_id",
    "new_shot_id",
    "panel_intervals_from_panels",
    "save_shot_schedule",
    "save_storyboard",
    "to_html",
    "to_markdown",
]
