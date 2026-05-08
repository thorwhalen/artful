"""Round-trip a :class:`Storyboard` through a lacing store.

Persistence model:

- Each :class:`PanelBody` is stored as a :class:`lacing.Annotation` whose
  ``body`` is the panel body, ``body_schema_uri`` is
  :data:`PANEL_BODY_SCHEMA_URI`, ``reference`` is a :class:`lacing.MediaRef`
  (asset_id of the timeline + the panel's interval), and ``tier`` is the
  storyboard title (or "storyboard" by default).

- The storyboard's ``style`` and ``aspect`` (no per-panel interval) are
  stored as one *timeless* annotation tagged with the same tier name and a
  small distinct body schema URI.

This way every adapter lacing already supports (TextGrid, EAF, JAMS, OTIO,
WebVTT, Web Annotation, JAMS, Label Studio, …) can round-trip a storyboard
unchanged. Apps add storyboard semantics by reading panels via
:func:`load_storyboard`; the underlying lacing store stays the single SSOT.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Iterable, Optional

from lacing import (
    Annotation,
    IntervalAnnotationStore,
    MediaRef,
    Provenance,
    TimeInterval,
)
from lacing.artifact import _now_rt

from .schema import (
    PANEL_BODY_SCHEMA_URI,
    PanelBody,
    Storyboard,
)


# A storyboard-level meta record (style, aspect, title) lives under a sibling
# body schema. Registered lazily so importing artful.store doesn't double-
# register if artful.schema was already imported.

STORYBOARD_META_BODY_SCHEMA_URI = "annot://schema/storyboard-meta/v1"


from pydantic import BaseModel, ConfigDict


class StoryboardMetaBody(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    title: str = ""
    style: str = ""
    aspect: str = "16:9"


_meta_registered = False


def _ensure_meta_registered() -> None:
    global _meta_registered
    if _meta_registered:
        return
    from lacing import register_body_schema
    try:
        register_body_schema(STORYBOARD_META_BODY_SCHEMA_URI, StoryboardMetaBody)
    except Exception:
        # If already registered (re-import), that's fine.
        pass
    _meta_registered = True


_ensure_meta_registered()


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------


_DEFAULT_TIER = "storyboard"


def save_storyboard(
    storyboard: Storyboard,
    store: IntervalAnnotationStore,
    *,
    panel_intervals: dict[str, TimeInterval],
    tier: str = _DEFAULT_TIER,
    was_attributed_to: str = "user:unknown",
    was_generated_by: str = "agent:artful",
) -> list[Annotation]:
    """Persist ``storyboard`` into ``store``.

    Args:
        storyboard: The :class:`Storyboard` to persist.
        store: A lacing store (any :class:`IntervalAnnotationStore`).
        panel_intervals: Per-panel-id mapping to a :class:`lacing.TimeInterval`.
            Required because :class:`PanelBody` itself does not carry the
            interval (it lives on the annotation's reference); the caller must
            tell us which time span each panel covers.
        tier: Tier name for the persisted annotations. Defaults to
            ``"storyboard"`` so multiple storyboards over the same asset can
            be distinguished by tier.
        was_attributed_to / was_generated_by: Provenance fields applied to
            every persisted annotation.

    Returns:
        The list of persisted :class:`Annotation` instances (panels, then meta).
    """
    out: list[Annotation] = []
    prov = _make_prov(was_generated_by, was_attributed_to)

    for panel in storyboard.panels:
        if panel.panel_id not in panel_intervals:
            raise KeyError(
                f"save_storyboard: no interval given for panel_id={panel.panel_id!r}"
            )
        interval = panel_intervals[panel.panel_id]
        ann = Annotation(
            id=_uuid.uuid4(),
            tier=tier,
            reference=MediaRef(asset_id=storyboard.asset_id, interval=interval),
            body=panel.model_dump(),
            body_schema_uri=PANEL_BODY_SCHEMA_URI,
            provenance=prov,
        )
        store.add(ann)
        out.append(ann)

    # Storyboard-level meta as a timeless annotation.
    if storyboard.title or storyboard.style or storyboard.aspect != "16:9":
        meta_body = StoryboardMetaBody(
            title=storyboard.title,
            style=storyboard.style,
            aspect=storyboard.aspect,
        )
        meta_ann = Annotation(
            id=_uuid.uuid4(),
            tier=tier,
            # Timeless annotation: no interval. Use a placeholder MediaRef
            # with a zero-duration interval at t=0 — lacing accepts it.
            reference=MediaRef(
                asset_id=storyboard.asset_id,
                interval=TimeInterval.from_seconds(0, 0),
            ),
            body=meta_body.model_dump(),
            body_schema_uri=STORYBOARD_META_BODY_SCHEMA_URI,
            provenance=prov,
        )
        store.add(meta_ann)
        out.append(meta_ann)

    return out


def load_storyboard(
    store: IntervalAnnotationStore,
    *,
    asset_id: str,
    tier: str = _DEFAULT_TIER,
) -> Storyboard:
    """Read panels from ``store`` and reconstruct a :class:`Storyboard`.

    Filters by ``tier`` (default ``"storyboard"``) and ``asset_id`` (so a
    store holding multiple storyboards over multiple assets stays clean).
    Panels are returned ordered by interval start.
    """
    panels: list[tuple[TimeInterval, PanelBody]] = []
    title = ""
    style = ""
    aspect = "16:9"

    for ann in store.all():
        if ann.tier != tier:
            continue
        if not isinstance(ann.reference, MediaRef):
            continue
        if ann.reference.asset_id != asset_id:
            continue
        if ann.body_schema_uri == PANEL_BODY_SCHEMA_URI:
            panel = PanelBody.model_validate(ann.body)
            panels.append((ann.reference.interval, panel))
        elif ann.body_schema_uri == STORYBOARD_META_BODY_SCHEMA_URI:
            meta = StoryboardMetaBody.model_validate(ann.body)
            title = meta.title
            style = meta.style
            aspect = meta.aspect

    panels.sort(key=lambda pair: pair[0].start.to_seconds())
    return Storyboard(
        title=title,
        asset_id=asset_id,
        panels=tuple(p for _, p in panels),
        style=style,
        aspect=aspect,
    )


def panel_intervals_from_panels(
    panels: Iterable[tuple[str, float, float]]
) -> dict[str, TimeInterval]:
    """Convenience: build the panel_intervals dict for :func:`save_storyboard`.

    Takes an iterable of ``(panel_id, start_s, end_s)`` triples. Returns a
    dict keyed by panel_id with TimeInterval values.
    """
    return {
        pid: TimeInterval.from_seconds(start_s, end_s)
        for pid, start_s, end_s in panels
    }


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _make_prov(was_generated_by: str, was_attributed_to: str) -> Provenance:
    return Provenance(
        was_generated_by=was_generated_by,
        was_attributed_to=was_attributed_to,
        was_derived_from=[],
        generated_at_time=_now_rt(),
        activity="create",
    )
