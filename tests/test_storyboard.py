"""Tests for artful — Storyboard schema, store round-trip, exports."""

from __future__ import annotations

import pytest

from lacing import MemoryStore, TimeInterval, validate_body

from artful import (
    PANEL_BODY_SCHEMA_URI,
    PanelBody,
    PanelImage,
    Storyboard,
    from_markdown,
    load_storyboard,
    new_panel_id,
    panel_intervals_from_panels,
    save_storyboard,
    to_html,
    to_markdown,
)


# --- schema ----------------------------------------------------------------


def test_panel_body_schema_registered_in_lacing():
    """The body schema is registered at import; lacing.validate_body uses it."""
    body = {
        "panel_id": "p001",
        "shot_id": "s01",
        "images": [],
        "caption": "Thor at the piano",
        "framing": "medium",
        "camera": "static",
        "transition_in": "cut",
        "notes": "",
    }
    # Validate via lacing's registered-schema path. Returns the validated model.
    result = validate_body(body, PANEL_BODY_SCHEMA_URI)
    assert result.panel_id == "p001"


def test_panel_body_schema_rejects_unknown_fields():
    body = {
        "panel_id": "p001",
        "rogue_field": 42,
    }
    with pytest.raises(Exception):  # pydantic validation
        validate_body(body, PANEL_BODY_SCHEMA_URI)


def test_new_panel_id_is_short_and_unique():
    a = new_panel_id()
    b = new_panel_id()
    assert a != b
    assert a.startswith("p")
    assert 5 <= len(a) <= 10


def test_panel_image_path_or_url_or_artifact_id():
    a = PanelImage(path="img.png")
    assert a.path == "img.png"
    b = PanelImage(url="https://x/img.png")
    assert b.url.endswith("img.png")
    c = PanelImage(artifact_id="0" * 64)
    assert c.artifact_id == "0" * 64


# --- store round-trip ------------------------------------------------------


def _build_storyboard():
    return Storyboard(
        title="The Bells — v1",
        asset_id="song-asset-id-abc",
        panels=(
            PanelBody(
                panel_id="p1",
                shot_id="s01",
                images=(PanelImage(path="composite.png", role="seed"),),
                caption="Thor at the piano",
                framing="medium",
                camera="static",
            ),
            PanelBody(
                panel_id="p2",
                shot_id="s02",
                images=(),
                caption="Bells over winter sky",
                framing="wide",
                camera="slow push-in",
            ),
        ),
        style="noir, candlelight",
        aspect="16:9",
    )


def test_save_then_load_roundtrip():
    sb = _build_storyboard()
    intervals = panel_intervals_from_panels([
        ("p1", 0.0, 4.0),
        ("p2", 4.0, 8.0),
    ])
    store = MemoryStore()
    save_storyboard(sb, store, panel_intervals=intervals)
    loaded = load_storyboard(store, asset_id=sb.asset_id)
    assert loaded.title == sb.title
    assert loaded.style == sb.style
    assert loaded.aspect == sb.aspect
    assert len(loaded.panels) == len(sb.panels)
    # Panels arrive sorted by interval start.
    assert loaded.panels[0].panel_id == "p1"
    assert loaded.panels[1].panel_id == "p2"
    assert loaded.panels[0].caption == "Thor at the piano"


def test_save_requires_interval_for_every_panel():
    sb = _build_storyboard()
    intervals = panel_intervals_from_panels([("p1", 0.0, 4.0)])  # missing p2
    store = MemoryStore()
    with pytest.raises(KeyError, match="p2"):
        save_storyboard(sb, store, panel_intervals=intervals)


def test_load_filters_by_asset_id():
    """Two storyboards over different assets in one store stay separate."""
    sb_a = Storyboard(asset_id="A", panels=(
        PanelBody(panel_id="pa", caption="a"),
    ))
    sb_b = Storyboard(asset_id="B", panels=(
        PanelBody(panel_id="pb", caption="b"),
    ))
    store = MemoryStore()
    save_storyboard(sb_a, store, panel_intervals={"pa": TimeInterval.from_seconds(0, 1)})
    save_storyboard(sb_b, store, panel_intervals={"pb": TimeInterval.from_seconds(0, 1)})

    loaded_a = load_storyboard(store, asset_id="A")
    loaded_b = load_storyboard(store, asset_id="B")
    assert len(loaded_a.panels) == 1 and loaded_a.panels[0].caption == "a"
    assert len(loaded_b.panels) == 1 and loaded_b.panels[0].caption == "b"


def test_load_filters_by_tier():
    sb = _build_storyboard()
    intervals = panel_intervals_from_panels([
        ("p1", 0.0, 4.0), ("p2", 4.0, 8.0),
    ])
    store = MemoryStore()
    save_storyboard(sb, store, panel_intervals=intervals, tier="alt-storyboard")
    # Default tier = "storyboard" finds nothing.
    default = load_storyboard(store, asset_id=sb.asset_id)
    assert default.panels == ()
    alt = load_storyboard(store, asset_id=sb.asset_id, tier="alt-storyboard")
    assert len(alt.panels) == 2


# --- markdown export / import --------------------------------------------


def test_markdown_round_trip_preserves_fields():
    sb = _build_storyboard()
    intervals = panel_intervals_from_panels([("p1", 0.0, 4.0), ("p2", 4.0, 8.0)])
    md = to_markdown(sb, intervals)
    sb2, ivs2 = from_markdown(md)

    assert sb2.title == sb.title
    assert sb2.asset_id == sb.asset_id
    assert sb2.style == sb.style
    assert sb2.aspect == sb.aspect
    assert len(sb2.panels) == len(sb.panels)
    for p_in, p_out in zip(sb.panels, sb2.panels):
        assert p_in.panel_id == p_out.panel_id
        assert p_in.shot_id == p_out.shot_id
        assert p_in.framing == p_out.framing
        assert p_in.camera == p_out.camera
        assert p_in.caption == p_out.caption
    assert ivs2["p1"].start.to_seconds() == 0.0
    assert ivs2["p1"].end.to_seconds() == 4.0


def test_markdown_includes_image_refs():
    sb = Storyboard(
        title="t", asset_id="x",
        panels=(PanelBody(
            panel_id="p1",
            images=(
                PanelImage(path="thumb.png", caption="thumb", role="thumbnail"),
                PanelImage(url="https://x/seed.png", role="seed", caption="seed"),
                PanelImage(artifact_id="a" * 64, caption="from-artifact"),
            ),
        ),),
    )
    md = to_markdown(sb)
    assert "![thumb](thumb.png)" in md
    assert "![seed](https://x/seed.png)" in md
    assert "artifact:" in md  # the artifact reference shows up


def test_markdown_image_refs_round_trip():
    sb = Storyboard(
        title="t", asset_id="x",
        panels=(PanelBody(
            panel_id="p1",
            images=(
                PanelImage(path="thumb.png", caption="thumb"),
                PanelImage(url="https://x/seed.png", caption="seed"),
                PanelImage(artifact_id="a" * 64, caption="art"),
            ),
        ),),
    )
    md = to_markdown(sb)
    sb2, _ = from_markdown(md)
    imgs = sb2.panels[0].images
    assert len(imgs) == 3
    # Path / URL / artifact_id distinctions are reconstructed from the prefix.
    assert imgs[0].path == "thumb.png" and imgs[0].url is None
    assert imgs[1].url == "https://x/seed.png" and imgs[1].path is None
    assert imgs[2].artifact_id == "a" * 64


# --- HTML ------------------------------------------------------------------


def test_html_includes_title_and_panels():
    sb = _build_storyboard()
    intervals = panel_intervals_from_panels([("p1", 0, 4), ("p2", 4, 8)])
    html = to_html(sb, intervals)
    assert "The Bells" in html
    assert "panel p1" in html
    assert "panel p2" in html
    assert "16:9" in html


def test_html_escapes_special_chars():
    sb = Storyboard(
        title="<hostile>",
        asset_id="x",
        panels=(PanelBody(panel_id="p1", caption="A & B <script>"),),
    )
    html = to_html(sb)
    assert "<hostile>" not in html  # escaped to &lt;hostile&gt;
    assert "&lt;hostile&gt;" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# --- shot grammar (spec §6.3) controlled-vocabulary fields ----------------


def test_panel_accepts_shot_grammar_fields():
    p = PanelBody(panel_id="p1", shot_size="CU", angle="OTS", movement="DOLLY_IN")
    assert p.shot_size == "CU"
    assert p.angle == "OTS"
    assert p.movement == "DOLLY_IN"
    # Distinct from the free-text framing/camera fields.
    assert p.framing == ""
    assert p.camera == ""
    # Validates as a storyboard-panel body in lacing.
    validate_body(p.model_dump(), PANEL_BODY_SCHEMA_URI)


def test_shot_grammar_defaults_none():
    p = PanelBody(panel_id="p1")
    assert p.shot_size is None
    assert p.angle is None
    assert p.movement is None


def test_panel_rejects_invalid_shot_grammar_value():
    with pytest.raises(Exception):
        PanelBody(panel_id="p1", shot_size="HUGE")  # not in the taxonomy


def test_markdown_round_trip_preserves_shot_grammar():
    sb = Storyboard(
        title="t",
        asset_id="x",
        panels=(
            PanelBody(
                panel_id="p1",
                shot_size="WS",
                angle="LOW",
                movement="PAN",
                framing="wide",
                camera="pan-left",
            ),
            PanelBody(panel_id="p2"),  # no shot grammar — stays None
        ),
    )
    md = to_markdown(sb)
    assert "shot_size: WS" in md
    assert "angle: LOW" in md
    assert "movement: PAN" in md
    sb2, _ = from_markdown(md)
    p1 = sb2.panel("p1")
    assert p1.shot_size == "WS"
    assert p1.angle == "LOW"
    assert p1.movement == "PAN"
    p2 = sb2.panel("p2")
    assert p2.shot_size is None
    assert p2.angle is None
    assert p2.movement is None


def test_markdown_unknown_shot_grammar_degrades_to_none():
    # A corrupt / hand-edited markdown value should degrade gracefully, not
    # raise — matching how the rest of the adapter tolerates bad input.
    md = "# t\n\n- asset_id: `x`\n\n## panel p1\n\n- shot_size: BOGUS\n\ncap\n"
    sb, _ = from_markdown(md)
    assert sb.panel("p1").shot_size is None
