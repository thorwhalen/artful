"""Storyboard exporters: Markdown ↔ HTML ↔ Storyboard.

Three forms supported today:

- :func:`to_markdown` / :func:`from_markdown` — round-trippable plain text
  for editor-friendly hand authoring + LLM consumption. Markdown is the
  canonical "give an LLM a storyboard to read or write" format.
- :func:`to_html` — a self-contained HTML contact sheet for review in a
  browser; embeds <img> tags pointing at the panels' urls / paths.

PDF export is deferred (needs reportlab; lives behind the ``[pdf]`` extra).

Each panel renders the same fields: panel id, time interval, framing, camera,
caption, image refs, notes. Round-trip-safe means: ``from_markdown(to_markdown(s))``
preserves every field.
"""

from __future__ import annotations

import html as _html
import re
from typing import Optional, get_args

from lacing import TimeInterval

from .schema import (
    Angle,
    Movement,
    PanelBody,
    PanelImage,
    ShotSize,
    Storyboard,
    new_panel_id,
)


# Controlled shot-grammar vocabularies (spec §6.3). Used by ``from_markdown``
# to validate parsed values and degrade gracefully (None) on unknown input.
_SHOT_SIZES: frozenset[str] = frozenset(get_args(ShotSize))
_ANGLES: frozenset[str] = frozenset(get_args(Angle))
_MOVEMENTS: frozenset[str] = frozenset(get_args(Movement))


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def to_markdown(
    storyboard: Storyboard,
    panel_intervals: dict[str, TimeInterval] | None = None,
) -> str:
    """Render ``storyboard`` as Markdown.

    If ``panel_intervals`` is given, each panel's heading includes its
    ``[start..end]s`` interval. If not, only ids are shown — useful when
    the intervals haven't been pinned yet.
    """
    out: list[str] = []
    title = storyboard.title or "Storyboard"
    out.append(f"# {title}")
    out.append("")
    out.append(f"- asset_id: `{storyboard.asset_id}`")
    if storyboard.style:
        out.append(f"- style: {storyboard.style}")
    out.append(f"- aspect: {storyboard.aspect}")
    out.append("")

    for panel in storyboard.panels:
        head = f"## panel {panel.panel_id}"
        if panel_intervals and panel.panel_id in panel_intervals:
            iv = panel_intervals[panel.panel_id]
            head += f" [{iv.start.to_seconds():.2f}..{iv.end.to_seconds():.2f}]s"
        out.append(head)
        out.append("")
        if panel.shot_id:
            out.append(f"- shot: `{panel.shot_id}`")
        if panel.framing:
            out.append(f"- framing: {panel.framing}")
        if panel.camera:
            out.append(f"- camera: {panel.camera}")
        # Controlled shot-grammar vocabulary (spec §6.3) — distinct from the
        # free-text framing/camera above.
        if panel.shot_size:
            out.append(f"- shot_size: {panel.shot_size}")
        if panel.angle:
            out.append(f"- angle: {panel.angle}")
        if panel.movement:
            out.append(f"- movement: {panel.movement}")
        if panel.transition_in and panel.transition_in != "cut":
            out.append(f"- transition: {panel.transition_in}")
        out.append("")
        if panel.caption:
            out.append(panel.caption)
            out.append("")
        for img in panel.images:
            ref = (
                img.path
                or img.url
                or (f"artifact:{img.artifact_id}" if img.artifact_id else "")
            )
            cap = img.caption or img.role
            if ref:
                out.append(f"![{cap}]({ref})")
        if panel.notes:
            out.append("")
            out.append(f"> notes: {panel.notes}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


_HEADING_RE = re.compile(r"^#\s+(.+)$")
_PANEL_RE = re.compile(
    r"^##\s+panel\s+(?P<id>\S+)(?:\s+\[(?P<start>[\d.]+)\.\.(?P<end>[\d.]+)\]s)?\s*$"
)
_TOP_FIELD_RE = re.compile(r"^-\s+(?P<key>[a-z_]+):\s*(?P<value>.*)$")
_IMG_RE = re.compile(r"!\[(?P<cap>[^\]]*)\]\((?P<src>[^)]+)\)")
_NOTES_RE = re.compile(r"^>\s*notes:\s*(?P<text>.*)$")


def from_markdown(
    text: str,
) -> tuple[Storyboard, dict[str, TimeInterval]]:
    """Parse :func:`to_markdown`'s output back into a Storyboard + intervals.

    Lines that don't match a known shape are appended to the current panel's
    caption. Panels without an interval in the heading are returned with
    no entry in the intervals dict (caller can pin them later).
    """
    title = ""
    asset_id = ""
    style = ""
    aspect = "16:9"
    panels: list[PanelBody] = []
    intervals: dict[str, TimeInterval] = {}

    current_id: Optional[str] = None
    current_shot: Optional[str] = None
    current_framing = ""
    current_camera = ""
    current_shot_size: Optional[str] = None
    current_angle: Optional[str] = None
    current_movement: Optional[str] = None
    current_transition = "cut"
    current_caption_lines: list[str] = []
    current_notes = ""
    current_images: list[PanelImage] = []

    in_top = True

    def _flush_panel():
        if current_id is None:
            return
        panel = PanelBody(
            panel_id=current_id,
            shot_id=current_shot,
            images=tuple(current_images),
            caption="\n".join(l for l in current_caption_lines if l).strip(),
            framing=current_framing,
            camera=current_camera,
            shot_size=current_shot_size,  # type: ignore[arg-type]
            angle=current_angle,  # type: ignore[arg-type]
            movement=current_movement,  # type: ignore[arg-type]
            transition_in=current_transition,
            notes=current_notes,
        )
        panels.append(panel)

    for raw in text.splitlines():
        line = raw.rstrip()

        # Top-level heading (only the first one is the title).
        m = _HEADING_RE.match(line)
        if m and not panels and current_id is None and in_top:
            title = m.group(1).strip()
            continue

        m = _PANEL_RE.match(line)
        if m:
            in_top = False
            _flush_panel()
            current_id = m.group("id")
            current_shot = None
            current_framing = ""
            current_camera = ""
            current_shot_size = None
            current_angle = None
            current_movement = None
            current_transition = "cut"
            current_caption_lines = []
            current_notes = ""
            current_images = []
            if m.group("start") is not None:
                start_s = float(m.group("start"))
                end_s = float(m.group("end"))
                intervals[current_id] = TimeInterval.from_seconds(start_s, end_s)
            continue

        if in_top:
            m = _TOP_FIELD_RE.match(line)
            if m:
                key, value = m.group("key"), m.group("value").strip()
                if key == "asset_id":
                    asset_id = _strip_code(value)
                elif key == "style":
                    style = value
                elif key == "aspect":
                    aspect = value
            continue

        # We're inside a panel.
        m = _TOP_FIELD_RE.match(line)
        if m:
            key, value = m.group("key"), m.group("value").strip()
            if key == "shot":
                current_shot = _strip_code(value)
            elif key == "framing":
                current_framing = value
            elif key == "camera":
                current_camera = value
            elif key == "shot_size":
                current_shot_size = value if value in _SHOT_SIZES else None
            elif key == "angle":
                current_angle = value if value in _ANGLES else None
            elif key == "movement":
                current_movement = value if value in _MOVEMENTS else None
            elif key == "transition":
                current_transition = value
            continue

        m = _IMG_RE.match(line)
        if m:
            cap = m.group("cap").strip()
            src = m.group("src").strip()
            current_images.append(_image_from_src(src, caption=cap))
            continue

        m = _NOTES_RE.match(line)
        if m:
            current_notes = m.group("text").strip()
            continue

        # Otherwise: caption text.
        if line:
            current_caption_lines.append(line)

    _flush_panel()
    return (
        Storyboard(
            title=title,
            asset_id=asset_id,
            panels=tuple(panels),
            style=style,
            aspect=aspect,
        ),
        intervals,
    )


def _strip_code(s: str) -> str:
    if s.startswith("`") and s.endswith("`"):
        return s[1:-1]
    return s


def _image_from_src(src: str, *, caption: str = "") -> PanelImage:
    if src.startswith("artifact:"):
        return PanelImage(artifact_id=src[len("artifact:") :], caption=caption)
    if src.startswith(("http://", "https://", "s3://", "gs://")):
        return PanelImage(url=src, caption=caption)
    return PanelImage(path=src, caption=caption)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def to_html(
    storyboard: Storyboard,
    panel_intervals: dict[str, TimeInterval] | None = None,
) -> str:
    """Render a self-contained HTML contact sheet."""
    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append('<html><head><meta charset="utf-8">')
    parts.append(f"<title>{_html.escape(storyboard.title or 'Storyboard')}</title>")
    parts.append("<style>")
    parts.append("""
body { font: 14px/1.4 -apple-system, system-ui, sans-serif; margin: 2rem; max-width: 980px; }
h1 { margin-bottom: 0.25rem; }
.meta { color: #555; margin-bottom: 1.5rem; }
.panel { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; margin: 1.5rem 0; padding: 1rem; border: 1px solid #ddd; border-radius: 6px; }
.panel img { width: 100%; max-width: 280px; border-radius: 4px; }
.panel-meta { color: #555; font-size: 0.9em; }
.panel h3 { margin: 0 0 0.5rem; }
.notes { color: #888; font-style: italic; margin-top: 0.5rem; }
""")
    parts.append("</style></head><body>")

    parts.append(f"<h1>{_html.escape(storyboard.title or 'Storyboard')}</h1>")
    parts.append('<div class="meta">')
    parts.append(f"asset_id: <code>{_html.escape(storyboard.asset_id)}</code>")
    if storyboard.style:
        parts.append(f" · style: {_html.escape(storyboard.style)}")
    parts.append(f" · aspect: {_html.escape(storyboard.aspect)}")
    parts.append("</div>")

    for panel in storyboard.panels:
        parts.append('<div class="panel">')
        parts.append("<div>")
        if panel.images:
            for img in panel.images:
                ref = img.path or img.url or ""
                if ref:
                    parts.append(
                        f'<img src="{_html.escape(ref)}" alt="{_html.escape(img.caption or img.role)}">'
                    )
        else:
            parts.append("<em>(no image)</em>")
        parts.append("</div>")

        parts.append("<div>")
        head = f"panel {_html.escape(panel.panel_id)}"
        if panel_intervals and panel.panel_id in panel_intervals:
            iv = panel_intervals[panel.panel_id]
            head += f" [{iv.start.to_seconds():.2f}..{iv.end.to_seconds():.2f}]s"
        parts.append(f"<h3>{head}</h3>")
        meta_bits: list[str] = []
        if panel.shot_id:
            meta_bits.append(f"shot <code>{_html.escape(panel.shot_id)}</code>")
        if panel.framing:
            meta_bits.append(_html.escape(panel.framing))
        if panel.camera:
            meta_bits.append(_html.escape(panel.camera))
        if panel.shot_size:
            meta_bits.append(_html.escape(panel.shot_size))
        if panel.angle:
            meta_bits.append(_html.escape(panel.angle))
        if panel.movement and panel.movement != "LOCKED":
            meta_bits.append(_html.escape(panel.movement))
        if panel.transition_in and panel.transition_in != "cut":
            meta_bits.append(f"transition: {_html.escape(panel.transition_in)}")
        if meta_bits:
            parts.append(f'<div class="panel-meta">{" · ".join(meta_bits)}</div>')
        if panel.caption:
            parts.append(f"<p>{_html.escape(panel.caption)}</p>")
        if panel.notes:
            parts.append(f'<div class="notes">notes: {_html.escape(panel.notes)}</div>')
        parts.append("</div>")
        parts.append("</div>")

    parts.append("</body></html>")
    return "\n".join(parts)
