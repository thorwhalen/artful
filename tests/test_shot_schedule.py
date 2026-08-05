"""Tests for artful.shot_schedule — the ``shot-schedule/v1`` body schema."""

from __future__ import annotations

import pytest

from lacing import MemoryStore, json_schema, validate_body
from lacing import schema as lacing_schema

from artful import (
    SHOT_SCHEDULE_BODY_SCHEMA_URI,
    SHOT_SCHEDULE_TIER,
    RiskFlag,
    ShotEntry,
    ShotScheduleBody,
    load_shot_schedule,
    load_shot_schedules,
    new_schedule_id,
    new_shot_id,
    save_shot_schedule,
)


# --- registration + URI ----------------------------------------------------


def test_uri_is_versioned_and_kebab_case():
    assert SHOT_SCHEDULE_BODY_SCHEMA_URI == "annot://schema/shot-schedule/v1"
    assert lacing_schema.parse_uri(SHOT_SCHEDULE_BODY_SCHEMA_URI) == (
        "shot-schedule",
        1,
    )


def test_schema_registered_in_lacing_at_import():
    assert lacing_schema.is_registered(SHOT_SCHEDULE_BODY_SCHEMA_URI)
    assert (
        lacing_schema.get_body_schema(SHOT_SCHEDULE_BODY_SCHEMA_URI) is ShotScheduleBody
    )


def test_default_tier():
    assert SHOT_SCHEDULE_TIER == "shot-schedule"


# --- JSON-Schema export ----------------------------------------------------


def test_json_schema_export_carries_the_constraint_fields():
    js = json_schema(SHOT_SCHEDULE_BODY_SCHEMA_URI)
    assert js["title"] == "ShotScheduleBody"
    assert set(js["properties"]) >= {
        "schedule_id",
        "model_id",
        "advised_for_model_id",
        "aspect",
        "resolution",
        "shots",
        "risk_flags",
    }
    # Nested models come through as $defs, so the FE codegen sees them.
    assert {"ShotEntry", "RiskFlag"} <= set(js["$defs"])
    entry_props = js["$defs"]["ShotEntry"]["properties"]
    assert {
        "max_duration_seconds",
        "max_characters_in_frame",
        "aspect",
        "resolution",
        "allow_last_frame_anchor",
        "take_budget",
        "clump_id",
        "risk_flags",
    } <= set(entry_props)


# --- vocabulary drift guards ----------------------------------------------


def test_risk_codes_match_the_reelee_shot_advisor_vocabulary():
    """``over_clip_cap`` / ``multi_character`` are the exact strings reelee's
    ShotWarning already emits. Renaming either here forks the vocabulary
    across the federation — this test is the tripwire. (artful cannot import
    reelee: the dependency runs the other way.)"""
    codes = set(_literal_values("RiskCode"))
    assert {"over_clip_cap", "multi_character"} <= codes
    assert codes == {
        "over_clip_cap",
        "multi_character",
        "first_last_frame",
        "dialogue_plus_action",
        "over_take_budget",
        "unsupported_resolution",
        "mixed_aspect_ratios",
    }


def test_risk_severity_matches_the_advisor_vocabulary():
    assert set(_literal_values("RiskSeverity")) == {"info", "warn"}


def test_shot_grammar_vocabulary_is_shared_not_redefined():
    """The schedule reuses artful's ShotSize/Angle/Movement objects — one
    taxonomy for the panel body and the schedule, not two copies."""
    from artful import Angle, Movement, ShotSize
    from artful import shot_schedule as ss

    assert ss.ShotSize is ShotSize
    assert ss.Angle is Angle
    assert ss.Movement is Movement


def test_duration_field_names_match_panel_body():
    """Same concept, same name as PanelBody — no ``est_duration_s`` fork."""
    from artful import PanelBody

    for field in ("duration_seconds_estimate", "duration_source"):
        assert field in PanelBody.model_fields
        assert field in ShotEntry.model_fields


def _literal_values(name: str) -> tuple[str, ...]:
    from typing import get_args

    from artful import shot_schedule as ss

    return get_args(getattr(ss, name))


# --- model + validation ----------------------------------------------------


def _build_schedule() -> ShotScheduleBody:
    return ShotScheduleBody(
        schedule_id="sch-001",
        title="Scene 4 — the pub",
        model_id="fal-ai/bytedance/seedance/v1/pro/image-to-video",
        advised_for_model_id="fal-ai/bytedance/seedance/v1/pro/image-to-video",
        aspect="16:9",
        resolution="720p",
        shots=(
            ShotEntry(
                shot_id="sh-01",
                panel_id="p1",
                beat_id="b1",
                description="Mairead pushes the door open.",
                characters=("Mairead",),
                shot_size="MS",
                angle="EYE_LEVEL",
                movement="LOCKED",
                duration_seconds_estimate=6.0,
                duration_source="estimate",
                max_duration_seconds=8.0,
                max_characters_in_frame=1,
                take_budget=3,
                clump_id="pub-interior",
            ),
            ShotEntry(
                shot_id="sh-02",
                description="She and Declan argue across the bar.",
                characters=("Mairead", "Declan"),
                shot_size="TWO_SHOT",
                duration_seconds_estimate=14.0,
                has_dialogue=True,
                has_action=True,
                max_characters_in_frame=1,
                clump_id="pub-interior",
                risk_flags=(
                    RiskFlag(
                        code="over_clip_cap",
                        message="~14s is over this model's ~10s clip cap.",
                        gotcha_id="seedance-clip-length-cap",
                    ),
                    RiskFlag(
                        code="multi_character",
                        message="2 characters — consider shot/reverse-shot.",
                        gotcha_id="single-character-per-frame",
                    ),
                ),
            ),
        ),
    )


def test_validates_through_the_lacing_registered_schema():
    sched = _build_schedule()
    result = validate_body(sched.model_dump(), SHOT_SCHEDULE_BODY_SCHEMA_URI)
    assert result.schedule_id == "sch-001"
    assert len(result.shots) == 2


def test_rejects_unknown_fields():
    with pytest.raises(Exception):
        validate_body(
            {"schedule_id": "s", "rogue_field": 42}, SHOT_SCHEDULE_BODY_SCHEMA_URI
        )


def test_shot_entry_rejects_unknown_fields():
    with pytest.raises(Exception):
        ShotEntry(shot_id="sh-01", est_duration_s=6.0)


def test_rejects_invalid_risk_code():
    with pytest.raises(Exception):
        RiskFlag(code="over-clip-cap")  # hyphenated is not the vocabulary


def test_rejects_out_of_range_constraints():
    with pytest.raises(Exception):
        ShotEntry(shot_id="a", max_characters_in_frame=0)
    with pytest.raises(Exception):
        ShotEntry(shot_id="a", take_budget=0)
    with pytest.raises(Exception):
        ShotEntry(shot_id="a", max_duration_seconds=0.0)
    with pytest.raises(Exception):
        ShotEntry(shot_id="a", duration_seconds_estimate=-1.0)


def test_rejects_invalid_shot_grammar_value():
    with pytest.raises(Exception):
        ShotEntry(shot_id="a", shot_size="HUGE")


def test_constraint_defaults_encode_the_safe_choice():
    """Anchoring both first and last frame contorts the subject, so the
    default must be *deny*, not allow."""
    e = ShotEntry(shot_id="a")
    assert e.allow_last_frame_anchor is False
    assert e.has_dialogue is False
    assert e.has_action is False
    assert e.take_budget is None
    assert e.max_duration_seconds is None
    assert e.max_characters_in_frame is None
    assert e.risk_flags == ()


def test_ordering_is_tuple_order_and_there_is_no_order_field():
    sched = _build_schedule()
    assert [s.shot_id for s in sched.shots] == ["sh-01", "sh-02"]
    assert "order" not in ShotEntry.model_fields


def test_character_count_derives_from_characters():
    """No separate count field that could drift from the names list."""
    assert "character_count" not in ShotEntry.model_fields
    e = ShotEntry(shot_id="a", characters=("Mairead", "Declan"))
    assert len(e.characters) == 2


def test_shot_lookup():
    sched = _build_schedule()
    assert sched.shot("sh-02").characters == ("Mairead", "Declan")
    assert sched.shot("nope") is None


def test_no_model_limits_are_copied_into_the_body():
    """falaw owns the model limit table; the schedule references it by
    ``model_id`` only. A copied ``max_clip_seconds`` here would be a second
    source of truth that silently goes stale."""
    forbidden = {
        "max_clip_seconds",
        "single_character_recommended",
        "supported_resolutions",
        "default_negative_prompt",
    }
    assert not (forbidden & set(ShotScheduleBody.model_fields))
    assert not (forbidden & set(ShotEntry.model_fields))


# --- staleness -------------------------------------------------------------


def test_needs_advice_is_false_when_flags_match_the_model():
    assert _build_schedule().needs_advice is False


def test_needs_advice_is_true_after_switching_model():
    sched = _build_schedule().model_copy(update={"model_id": "fal-ai/other/model"})
    assert sched.needs_advice is True


def test_needs_advice_is_true_when_never_advised():
    sched = ShotScheduleBody(schedule_id="s", model_id="fal-ai/some/model")
    assert sched.advised_for_model_id is None
    assert sched.needs_advice is True


def test_needs_advice_is_false_without_a_model():
    """A schedule with no model cannot be advised, so it never *needs* it."""
    assert ShotScheduleBody(schedule_id="s").needs_advice is False


# --- store round-trip ------------------------------------------------------


def test_save_then_load_roundtrip():
    sched = _build_schedule()
    store = MemoryStore()
    ann = save_shot_schedule(sched, store, asset_id="asset-abc")
    assert ann.body_schema_uri == SHOT_SCHEDULE_BODY_SCHEMA_URI
    assert ann.tier == SHOT_SCHEDULE_TIER

    loaded = load_shot_schedule(store, asset_id="asset-abc")
    assert loaded == sched  # every field, including nested risk flags


def test_roundtrip_preserves_risk_flags_and_constraints():
    sched = _build_schedule()
    store = MemoryStore()
    save_shot_schedule(sched, store, asset_id="asset-abc")
    loaded = load_shot_schedule(store, asset_id="asset-abc")

    sh2 = loaded.shot("sh-02")
    assert [f.code for f in sh2.risk_flags] == ["over_clip_cap", "multi_character"]
    assert sh2.risk_flags[0].gotcha_id == "seedance-clip-length-cap"
    assert sh2.risk_flags[0].severity == "warn"
    assert sh2.max_characters_in_frame == 1
    assert sh2.has_dialogue is True

    sh1 = loaded.shot("sh-01")
    assert sh1.take_budget == 3
    assert sh1.clump_id == "pub-interior"
    assert sh1.duration_seconds_estimate == 6.0
    assert sh1.shot_size == "MS"


def test_load_filters_by_asset_id():
    store = MemoryStore()
    save_shot_schedule(ShotScheduleBody(schedule_id="a"), store, asset_id="A")
    save_shot_schedule(ShotScheduleBody(schedule_id="b"), store, asset_id="B")
    assert load_shot_schedule(store, asset_id="A").schedule_id == "a"
    assert load_shot_schedule(store, asset_id="B").schedule_id == "b"


def test_load_filters_by_tier():
    store = MemoryStore()
    save_shot_schedule(
        ShotScheduleBody(schedule_id="a"), store, asset_id="A", tier="draft-schedule"
    )
    assert load_shot_schedule(store, asset_id="A") is None
    assert (
        load_shot_schedule(store, asset_id="A", tier="draft-schedule").schedule_id
        == "a"
    )


def test_load_ignores_other_body_schemas_on_the_same_tier():
    """A storyboard-meta record saved on the same tier must not be parsed
    as a schedule."""
    from artful import Storyboard, save_storyboard

    store = MemoryStore()
    save_storyboard(
        Storyboard(title="t", asset_id="A", style="noir"),
        store,
        panel_intervals={},
        tier=SHOT_SCHEDULE_TIER,
    )
    save_shot_schedule(ShotScheduleBody(schedule_id="a"), store, asset_id="A")
    assert [s.schedule_id for s in load_shot_schedules(store, asset_id="A")] == ["a"]


def test_load_returns_none_when_absent():
    assert load_shot_schedule(MemoryStore(), asset_id="nope") is None


def test_save_appends_so_revisions_are_kept():
    store = MemoryStore()
    save_shot_schedule(ShotScheduleBody(schedule_id="v1"), store, asset_id="A")
    save_shot_schedule(ShotScheduleBody(schedule_id="v2"), store, asset_id="A")
    ids = {s.schedule_id for s in load_shot_schedules(store, asset_id="A")}
    assert ids == {"v1", "v2"}


def test_load_by_schedule_id_selects_the_right_revision():
    store = MemoryStore()
    save_shot_schedule(ShotScheduleBody(schedule_id="v1"), store, asset_id="A")
    save_shot_schedule(ShotScheduleBody(schedule_id="v2"), store, asset_id="A")
    got = load_shot_schedule(store, asset_id="A", schedule_id="v2")
    assert got.schedule_id == "v2"
    assert load_shot_schedule(store, asset_id="A", schedule_id="v3") is None


def test_provenance_is_stamped():
    store = MemoryStore()
    ann = save_shot_schedule(
        ShotScheduleBody(schedule_id="a"),
        store,
        asset_id="A",
        was_attributed_to="user:noel",
        was_generated_by="agent:test",
    )
    assert ann.provenance.was_attributed_to == "user:noel"
    assert ann.provenance.was_generated_by == "agent:test"


# --- id helpers ------------------------------------------------------------


def test_id_helpers_are_short_prefixed_and_unique():
    a, b = new_shot_id(), new_shot_id()
    assert a != b and a.startswith("sh") and 6 <= len(a) <= 12
    c, d = new_schedule_id(), new_schedule_id()
    assert c != d and c.startswith("sch") and 7 <= len(c) <= 12
