"""Stability guard for the four body schemas artful owns.

These four URIs are *on the wire*. reelee and nw read and write annotations
carrying them, and real projects hold serialized copies of those bodies. So
unlike the rest of artful — where clean shape beats backward compatibility —
a change here is a federation event that needs a lacing migration.

This file pins two things per body:

- the **URI string**, because the URI is the contract; and
- the **serialized shape**: which fields exist, which are required, and each
  field's JSON type / constraints / default.

The shapes are read out of ``model_json_schema()`` (which pydantic emits
by-alias, so the pinned names are the names that land in ``Annotation.body``)
and rendered as short, readable expressions — ``"string|null = null"``,
``"array<ShotEntry>"``, ``"integer(minimum=1)|null = null"``. A diff on a
failing pin therefore says *what* changed, which a checksum could not.

Breaking and additive changes fail in different tests, with different advice:

- :func:`test_pinned_fields_are_unchanged` fires on a rename, a removal, a
  type change, a constraint change, or a default change — all breaking.
- :func:`test_new_fields_are_additive_and_pinned` fires on a field that
  exists but isn't pinned, and tells you whether it is additive (optional,
  with a default) or breaking (required).
"""

from __future__ import annotations

import json

import pytest

from lacing.schema import get_body_schema, registered_uris

from artful import (
    MODEL_SHEET_BODY_SCHEMA_URI,
    PANEL_BODY_SCHEMA_URI,
    SHOT_SCHEDULE_BODY_SCHEMA_URI,
    STORYBOARD_META_BODY_SCHEMA_URI,
    ModelSheet,
    PanelBody,
    ShotScheduleBody,
    StoryboardMetaBody,
)


MIGRATION_RULE = (
    "\n"
    "FEDERATION-VISIBLE SCHEMA CHANGE.\n"
    "artful owns four body-schema URIs that carry real user data — reelee and "
    "nw read and write them, and stored projects already hold them. Renaming a URI, renaming or "
    "removing a field, or changing a field's serialized type, constraint or "
    "default BREAKS every stored annotation and every downstream round-trip. "
    "It is not a rename you can land in one pass — it needs a new schema "
    "version plus a `lacing.register_migration` from the old one, and the "
    "downstream packages updated with it.\n"
    "See the 'Migration-required rule' section of this repo's CLAUDE.md.\n"
    "Only after the migration exists should the pin below be updated — in the "
    "same commit as the migration."
)


# --- the URIs --------------------------------------------------------------


def test_body_schema_uris_are_pinned():
    """The URI *is* the contract — stored annotations name it by string."""
    actual = {
        "PANEL_BODY_SCHEMA_URI": PANEL_BODY_SCHEMA_URI,
        "SHOT_SCHEDULE_BODY_SCHEMA_URI": SHOT_SCHEDULE_BODY_SCHEMA_URI,
        "MODEL_SHEET_BODY_SCHEMA_URI": MODEL_SHEET_BODY_SCHEMA_URI,
        "STORYBOARD_META_BODY_SCHEMA_URI": STORYBOARD_META_BODY_SCHEMA_URI,
    }
    assert actual == {
        "PANEL_BODY_SCHEMA_URI": "annot://schema/storyboard-panel/v1",
        "SHOT_SCHEDULE_BODY_SCHEMA_URI": "annot://schema/shot-schedule/v1",
        "MODEL_SHEET_BODY_SCHEMA_URI": "annot://schema/model-sheet/v1",
        "STORYBOARD_META_BODY_SCHEMA_URI": "annot://schema/storyboard-meta/v1",
    }, MIGRATION_RULE


#: URI → the model importing ``artful`` registers against it.
OWNED: dict[str, type] = {
    PANEL_BODY_SCHEMA_URI: PanelBody,
    SHOT_SCHEDULE_BODY_SCHEMA_URI: ShotScheduleBody,
    MODEL_SHEET_BODY_SCHEMA_URI: ModelSheet,
    STORYBOARD_META_BODY_SCHEMA_URI: StoryboardMetaBody,
}


@pytest.mark.parametrize("uri", sorted(OWNED))
def test_uri_resolves_to_its_pinned_model(uri):
    assert get_body_schema(uri) is OWNED[uri], MIGRATION_RULE


def test_artful_owns_exactly_these_four_body_schemas():
    """A fifth artful-owned schema must be pinned here too, or it ships
    unguarded. (Filtered to artful's own models: the lacing registry is
    global and other packages register into it as well.)"""
    owned = {
        uri
        for uri in registered_uris()
        if get_body_schema(uri).__module__.split(".")[0] == "artful"
    }
    assert owned == set(OWNED), (
        "artful registers a body schema this guard does not pin. Add it to "
        "OWNED and PINNED below." + MIGRATION_RULE
    )


@pytest.mark.parametrize("uri", sorted(OWNED))
def test_bodies_forbid_extra_fields(uri):
    """``extra="forbid"`` is part of the contract: reelee's LLM transforms
    rely on an unknown key raising rather than being silently dropped."""
    assert OWNED[uri].model_json_schema()["additionalProperties"] is False


# --- the serialized shapes -------------------------------------------------

# Controlled vocabularies shared by more than one body — one taxonomy, not a
# copy per carrier (see ``test_shot_grammar_vocabulary_is_shared_not_redefined``
# in test_shot_schedule.py). Members are sorted in the rendered shape, so
# reordering a Literal is not a failure; adding or dropping a member is.
SHOT_SIZE = "enum[CU|ECU|ELS|GROUP|INSERT|LS|MASTER|MCU|MS|MWS|THREE_SHOT|TWO_SHOT|WS]"
ANGLE = (
    "enum[BIRDS_EYE|DUTCH|EYE_LEVEL|HIGH|LOW|OTS|POV|PROFILE|THREE_QUARTER|WORMS_EYE]"
)
MOVEMENT = (
    "enum[CRANE|DOLLY_IN|DOLLY_OUT|DOLLY_ZOOM|HANDHELD|LOCKED|PAN|PEDESTAL"
    "|TILT|TRUCK|WHIP_PAN|ZOOM]"
)
DURATION_SOURCE = "enum[estimate|from_clip|from_voiceover|manual]"
REVIEW_STATUS = "enum[approved|needs-revision|rejected|unreviewed]"
MOMENT_HEURISTIC = (
    "enum[apex_of_action|decisive_composition|entry_for_clip|expression_over_action"
    "|eyeline_contact|held_breath|just_before_recognition|reaction_not_action"
    "|silhouette_test]"
)
MOMENT_TIMING = "enum[apex|entry|exit|mid]"
RISK_CODE = (
    "enum[dialogue_plus_action|first_last_frame|mixed_aspect_ratios|multi_character"
    "|over_clip_cap|over_take_budget|unsupported_resolution]"
)
MODEL_SHEET_VIEW = (
    "enum[back|front|side_left|side_right|three_quarter_back|three_quarter_front]"
)

#: Model name → its pinned ``required`` field names and per-field shapes.
#: Nested models (``PanelImage``, ``ShotEntry``, ``RiskFlag``) are pinned too:
#: they serialize *inside* a body, so their fields are equally on the wire.
PINNED: dict[str, dict] = {
    "PanelBody": {
        "required": ("panel_id",),
        "fields": {
            "panel_id": "string",
            "shot_id": "string|null = null",
            "images": "array<PanelImage>",
            "caption": 'string = ""',
            "framing": 'string = ""',
            "camera": 'string = ""',
            "transition_in": 'string = "cut"',
            "notes": 'string = ""',
            "review_status": f'{REVIEW_STATUS} = "unreviewed"',
            "active_image_index": "integer(minimum=0) = 0",
            "moment_caption": "string|null = null",
            "moment_heuristic": f"{MOMENT_HEURISTIC}|null = null",
            "moment_timing": f"{MOMENT_TIMING}|null = null",
            "moment_focal_character_ref": "string|null = null",
            "split_from_beat_id": "string|null = null",
            "split_index": "integer|null = null",
            "split_total": "integer|null = null",
            "split_reason": "string|null = null",
            "shot_size": f"{SHOT_SIZE}|null = null",
            "angle": f"{ANGLE}|null = null",
            "movement": f"{MOVEMENT}|null = null",
            "duration_seconds_estimate": "number(minimum=0.0)|null = null",
            "duration_source": f"{DURATION_SOURCE}|null = null",
            "duration_confidence": "number(maximum=1.0, minimum=0.0)|null = null",
            "duration_model_version": "string|null = null",
        },
    },
    "PanelImage": {
        "required": (),
        "fields": {
            "artifact_id": "string|null = null",
            "url": "string|null = null",
            "path": "string|null = null",
            "role": 'string = "thumbnail"',
            "caption": 'string = ""',
        },
    },
    "StoryboardMetaBody": {
        "required": (),
        "fields": {
            "title": 'string = ""',
            "style": 'string = ""',
            "aspect": 'string = "16:9"',
        },
    },
    "ModelSheet": {
        "required": ("character_ref_id", "sheet_id"),
        "fields": {
            "character_ref_id": "string",
            "sheet_id": "string",
            "canonical_views": f"object<{MODEL_SHEET_VIEW},string>",
            "expression_set": "object<string,string>",
            "costume_set": "object<string,string>",
            "palette_anchors": "array<string>",
            "distinguishing_features": "array<string>",
            "head_to_body_ratio": "number(exclusiveMinimum=0.0)|null = null",
            "do_not_do": "array<string>",
            "age_progression": "object<string,string>",
            "prop_interactions": "object<string,string>",
            "voice_personality_notes": "string|null = null",
        },
    },
    "ShotScheduleBody": {
        "required": ("schedule_id",),
        "fields": {
            "schedule_id": "string",
            "title": 'string = ""',
            "model_id": "string|null = null",
            "advised_for_model_id": "string|null = null",
            "aspect": 'string = "16:9"',
            "resolution": "string|null = null",
            "shots": "array<ShotEntry>",
            "risk_flags": "array<RiskFlag>",
            "notes": 'string = ""',
        },
    },
    "ShotEntry": {
        "required": ("shot_id",),
        "fields": {
            "shot_id": "string",
            "panel_id": "string|null = null",
            "beat_id": "string|null = null",
            "description": 'string = ""',
            "characters": "array<string>",
            "shot_size": f"{SHOT_SIZE}|null = null",
            "angle": f"{ANGLE}|null = null",
            "movement": f"{MOVEMENT}|null = null",
            "duration_seconds_estimate": "number(minimum=0.0)|null = null",
            "duration_source": f"{DURATION_SOURCE}|null = null",
            "max_duration_seconds": "number(exclusiveMinimum=0.0)|null = null",
            "max_characters_in_frame": "integer(minimum=1)|null = null",
            "aspect": "string|null = null",
            "resolution": "string|null = null",
            "allow_last_frame_anchor": "boolean = false",
            "has_dialogue": "boolean = false",
            "has_action": "boolean = false",
            "take_budget": "integer(minimum=1)|null = null",
            "clump_id": "string|null = null",
            "risk_flags": "array<RiskFlag>",
            "notes": 'string = ""',
        },
    },
    "RiskFlag": {
        "required": ("code",),
        "fields": {
            "code": RISK_CODE,
            "message": 'string = ""',
            "severity": 'enum[info|warn] = "warn"',
            "gotcha_id": "string|null = null",
        },
    },
}


@pytest.mark.parametrize("model_name", sorted(PINNED))
def test_pinned_fields_are_unchanged(model_name):
    """Every pinned field still exists, with the same serialized shape."""
    pinned = PINNED[model_name]
    actual = _actual_shapes()[model_name]
    still_there = {
        name: shape
        for name, shape in actual["fields"].items()
        if name in pinned["fields"]
    }
    assert still_there == pinned["fields"], (
        f"{model_name}: a pinned field was renamed, removed, retyped, "
        f"re-constrained or re-defaulted." + MIGRATION_RULE
    )
    assert actual["required"] == pinned["required"], (
        f"{model_name}: the set of REQUIRED fields changed. Making a field "
        f"required rejects every stored body without it; making one optional "
        f"lets a downstream writer omit it." + MIGRATION_RULE
    )


@pytest.mark.parametrize("model_name", sorted(PINNED))
def test_new_fields_are_additive_and_pinned(model_name):
    """A field that exists but isn't pinned — additive, or breaking?"""
    pinned = PINNED[model_name]
    actual = _actual_shapes()[model_name]
    unpinned = {
        name: shape
        for name, shape in actual["fields"].items()
        if name not in pinned["fields"]
    }
    if not unpinned:
        return
    breaking = sorted(n for n in unpinned if n in actual["required"])
    if breaking:
        pytest.fail(
            f"{model_name}: new REQUIRED field(s) {breaking} — every stored "
            f"body predates them and will now fail validation." + MIGRATION_RULE
        )
    pytest.fail(
        f"{model_name}: new optional field(s) {sorted(unpinned)}. That is an "
        f"ADDITIVE change — old bodies still load, no migration needed — but "
        f"the pin has to record it or this guard silently stops covering the "
        f"body. Add to PINNED[{model_name!r}]['fields'] in this same PR:\n  "
        + "\n  ".join(f"{n!r}: {s!r}," for n, s in sorted(unpinned.items()))
    )


# --- shape rendering -------------------------------------------------------
#
# Reduce one JSON-Schema property to a short expression a human can diff.
# Anything pydantic emits that isn't recognised below is appended verbatim as
# ``key=value`` rather than dropped, so an unanticipated keyword still shows
# up in the failure diff instead of slipping through unpinned.

#: Prose, not contract — a reworded docstring must not fail the guard.
PROSE_KEYS = frozenset({"title", "description"})


def _actual_shapes() -> dict[str, dict]:
    """``{model name: {"required": (...), "fields": {name: shape}}}`` for the
    four owned bodies plus every model nested inside one of them."""
    out: dict[str, dict] = {}
    for model in OWNED.values():
        js = model.model_json_schema()
        out[js["title"]] = _entry(js)
        for name, sub in js.get("$defs", {}).items():
            out[name] = _entry(sub)
    return out


def _entry(js: dict) -> dict:
    return {
        "required": tuple(js.get("required", ())),
        "fields": {name: _shape(prop) for name, prop in js["properties"].items()},
    }


def _shape(prop: dict) -> str:
    prop = {k: v for k, v in prop.items() if k not in PROSE_KEYS}
    has_default = "default" in prop
    default = prop.pop("default", None)
    expr = _type_expr(prop)
    return f"{expr} = {json.dumps(default, sort_keys=True)}" if has_default else expr


def _type_expr(prop: dict) -> str:
    prop = {k: v for k, v in prop.items() if k not in PROSE_KEYS}
    if "anyOf" in prop:
        rest = {k: v for k, v in prop.items() if k != "anyOf"}
        return _with_extras("|".join(_type_expr(s) for s in prop["anyOf"]), rest)
    if "$ref" in prop:
        return prop["$ref"].rsplit("/", 1)[-1]
    rest = dict(prop)
    if "enum" in rest:
        members = "|".join(sorted(rest.pop("enum")))
        rest.pop("type", None)
        return _with_extras(f"enum[{members}]", rest)
    kind = rest.pop("type", "any")
    if kind == "array":
        return _with_extras(f"array<{_type_expr(rest.pop('items', {}))}>", rest)
    if kind == "object":
        values = rest.pop("additionalProperties", None)
        keys = rest.pop("propertyNames", None)
        key_expr = _type_expr(keys) if keys else "string"
        value_expr = _type_expr(values) if values is not None else "any"
        return _with_extras(f"object<{key_expr},{value_expr}>", rest)
    return _with_extras(kind, rest)


def _with_extras(base: str, extras: dict) -> str:
    if not extras:
        return base
    tail = ", ".join(
        f"{k}={json.dumps(v, sort_keys=True)}" for k, v in sorted(extras.items())
    )
    return f"{base}({tail})"
