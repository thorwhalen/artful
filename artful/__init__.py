"""artful — Storyboard data model and exporters.

A *storyboard* is a sequence of *panels* along a timeline. Each panel pins
an interval of the master asset (a song, video, podcast clip), optionally
points at a project shot, and carries one or more images plus directorial
annotations.

Panels are persisted as :class:`lacing.Annotation` records with body schema
``annot://schema/storyboard-panel/v1``. That means a storyboard is queryable
with lacing's full toolkit (Allen interval algebra, store backends, format
adapters) without artful having to reinvent any of it.

Public surface:

- :class:`Storyboard`, :class:`PanelBody`, :class:`PanelImage` — Pydantic
  models for in-memory work.
- :func:`save_storyboard` / :func:`load_storyboard` — round-trip with any
  :class:`lacing.IntervalAnnotationStore`.
- :func:`to_markdown` / :func:`from_markdown` — round-trip Markdown
  (the canonical format for LLM authoring).
- :func:`to_html` — self-contained HTML contact sheet for review.
"""

from .exports import from_markdown, to_html, to_markdown
from .schema import (
    PANEL_BODY_SCHEMA_URI,
    PanelBody,
    PanelImage,
    Storyboard,
    new_panel_id,
)
from .store import (
    STORYBOARD_META_BODY_SCHEMA_URI,
    StoryboardMetaBody,
    load_storyboard,
    panel_intervals_from_panels,
    save_storyboard,
)

__all__ = [
    "PANEL_BODY_SCHEMA_URI",
    "STORYBOARD_META_BODY_SCHEMA_URI",
    "PanelBody",
    "PanelImage",
    "Storyboard",
    "StoryboardMetaBody",
    "from_markdown",
    "load_storyboard",
    "new_panel_id",
    "panel_intervals_from_panels",
    "save_storyboard",
    "to_html",
    "to_markdown",
]
