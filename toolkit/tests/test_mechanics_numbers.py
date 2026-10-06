import html
import re
from typing import Any

import pytest

from mystery_forge.mechanics import numbers
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)
from mystery_forge.mechanics.registry import all_implementations

IMPLEMENTATIONS: dict[str, MechanicImplementation[Any]] = {
    implementation.id: implementation for implementation in numbers.IMPLEMENTATIONS
}
MECHANIC_IDS: list[str] = ["arithmetic-lock", "clock-faces"]


def make_context(answer: str, seed: int = 7) -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language="en", seed=seed, documents={})


def build(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic_id]
    return implementation.build(parse_params(implementation, raw_params), context)


def rendered_from(artifact: Artifact) -> RenderedArtifact:
    return RenderedArtifact(text=html.unescape(re.sub(r"<[^>]+>", "", artifact.html)), html=artifact.html)


def build_error(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(mechanic_id, raw_params, context)
    return raised.value


def assert_print_safe_svg(artifact: Artifact) -> None:
    assert "currentColor" in artifact.html
    assert "<script" not in artifact.html
    assert "http" not in artifact.html
    assert "style=" not in artifact.html
    assert all(color == "currentColor" for color in re.findall(r'(?:fill|stroke)="([^"n][^"]*)"', artifact.html))
    assert all(css_class.startswith("mf-") for css_class in re.findall(r'class="([^"]+)"', artifact.html))


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_number_mechanic_is_registered(mechanic_id: str) -> None:
    assert mechanic_id in all_implementations()


@pytest.mark.parametrize("mechanic_id", MECHANIC_IDS)
def test_number_params_describe_every_field(mechanic_id: str) -> None:
    schema: dict[str, Any] = IMPLEMENTATIONS[mechanic_id].params_model.model_json_schema()
    models: list[dict[str, Any]] = [schema, *schema.get("$defs", {}).values()]
    assert all(field.get("description") for model in models for field in model["properties"].values())


@pytest.mark.parametrize(
    ("mechanic_id", "params"),
    [("arithmetic-lock", {"steps": [{"label": "a", "value": 1}], "expression": "a"}), ("clock-faces", {})],
)
def test_number_mechanic_rejects_an_answer_that_is_not_digits(mechanic_id: str, params: dict[str, Any]) -> None:
    error: MechanicBuildError = build_error(mechanic_id, params, make_context("Mill 7"))
    assert error.message == "The answer 'Mill 7' is not a number made of digits only."
    assert "digits" in error.fix_hint


# arithmetic-lock

LOCK_STEPS: list[dict[str, Any]] = [{"label": "boxes", "value": "12"}, {"label": "keys", "value": "7"}]


def lock_error(expression: str, answer: str = "0040", steps: list[dict[str, Any]] = LOCK_STEPS) -> MechanicBuildError:
    return build_error("arithmetic-lock", {"steps": steps, "expression": expression}, make_context(answer))


def test_arithmetic_lock_accepts_an_expression_that_gives_the_answer_and_draws_its_dials() -> None:
    params: dict[str, Any] = {"steps": LOCK_STEPS, "expression": "(boxes * keys - 4) // 2"}
    artifact: Artifact = build("arithmetic-lock", params, make_context("0040"))
    assert artifact.html.count('class="mf-lock-dial"') == 4
    assert 'data-dials="4"' in artifact.html
    assert artifact.solver_text == "A combination lock with 4 digit dials."
    assert_print_safe_svg(artifact)


def test_arithmetic_lock_allows_a_negative_sign_and_whole_numbers() -> None:
    build("arithmetic-lock", {"steps": LOCK_STEPS, "expression": "-keys + 49"}, make_context("42"))


def test_arithmetic_lock_rejects_a_result_that_is_not_the_answer() -> None:
    error: MechanicBuildError = lock_error("boxes + keys")
    assert error.message == "The expression 'boxes + keys' gives 19, but the answer is '0040'."
    assert "values" in error.fix_hint
    assert (
        lock_error("keys - boxes", answer="5").message
        == "The expression 'keys - boxes' gives -5, but the answer is '5'."
    )


@pytest.mark.parametrize(
    ("expression", "segment"),
    [("boxes / keys", "boxes / keys"), ("boxes ** 2", "boxes ** 2"), ("abs(keys)", "abs(keys)"), ("2.5", "2.5"),
     ("True", "True"), ("+keys", "+keys"), ("boxes.real", "boxes.real")],
)  # fmt: skip
def test_arithmetic_lock_rejects_operations_outside_the_safe_set(expression: str, segment: str) -> None:
    error: MechanicBuildError = lock_error(expression)
    assert error.message == f"The expression '{expression}' uses '{segment}', which the lock does not allow."
    assert "+ - * //" in error.fix_hint


def test_arithmetic_lock_rejects_syntax_errors_unknown_labels_and_division_by_zero() -> None:
    syntax: MechanicBuildError = lock_error("boxes +")
    assert syntax.message == "The expression 'boxes +' is not valid arithmetic."
    unknown: MechanicBuildError = lock_error("boxes + doors")
    assert unknown.message == "The expression 'boxes + doors' uses 'doors', which is not a step label."
    assert unknown.fix_hint == "Use only these labels: boxes, keys."
    assert lock_error("boxes // (keys - 7)").message == "The expression 'boxes // (keys - 7)' divides by zero."


@pytest.mark.parametrize("label", ["two words", "9lives", ""])
def test_arithmetic_lock_rejects_a_label_that_is_not_a_name(label: str) -> None:
    error: MechanicBuildError = lock_error("a", steps=[{"label": label, "value": 1}])
    assert error.message == f"The step label '{label}' is not a valid name."
    assert "underscores" in error.fix_hint


def test_arithmetic_lock_rejects_a_duplicate_label() -> None:
    steps: list[dict[str, Any]] = [{"label": "a", "value": 1}, {"label": "a", "value": 2}]
    error: MechanicBuildError = lock_error("a", steps=steps)
    assert error.message == "The step label 'a' appears more than once."
    assert "label" in error.fix_hint


def test_arithmetic_lock_dial_count_must_match_the_answer_length() -> None:
    params: dict[str, Any] = {"steps": LOCK_STEPS, "expression": "boxes", "digits": "3"}
    error: MechanicBuildError = build_error("arithmetic-lock", params, make_context("0012"))
    assert error.message == "The lock has 3 dials, but the answer '0012' has 4 digits."
    assert "digits" in error.fix_hint
    build("arithmetic-lock", {**params, "digits": 4}, make_context("0012"))


# clock-faces


def decode_clocks(artifact: Artifact, raw_params: dict[str, Any], context: MechanicContext) -> str:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS["clock-faces"]
    assert implementation.decode_rendered is not None
    return implementation.decode_rendered(rendered_from(artifact), parse_params(implementation, raw_params), context)


def hand_end(artifact: Artifact, hand: str) -> list[tuple[str, str]]:
    return re.findall(rf'<line class="mf-clock-{hand}" x1="50" y1="50" x2="([^"]+)" y2="([^"]+)"', artifact.html)


def test_clock_faces_hour_mode_points_the_hour_hand_at_each_digit() -> None:
    artifact: Artifact = build("clock-faces", {}, make_context("306"))
    assert re.findall(r'data-symbol="(\d)"', artifact.html) == ["3", "0", "6"]
    assert hand_end(artifact, "hour") == [("74", "50"), ("50", "26"), ("50", "74")]
    assert hand_end(artifact, "minute") == [("50", "14"), ("50", "14"), ("50", "14")]
    assert artifact.solver_text == "Clock 1 shows 3:00. Clock 2 shows 12:00. Clock 3 shows 6:00."
    assert_print_safe_svg(artifact)


def test_clock_faces_minute_mode_points_the_minute_hand_at_digit_times_five() -> None:
    artifact: Artifact = build("clock-faces", {"mode": "minute"}, make_context("30"))
    assert hand_end(artifact, "minute") == [("86", "50"), ("50", "14")]
    assert re.fullmatch(r"Clock 1 shows ([1-9]|1[0-2]):15\. Clock 2 shows ([1-9]|1[0-2]):00\.", artifact.solver_text)


def test_clock_faces_minute_mode_hours_depend_on_the_seed() -> None:
    first: Artifact = build("clock-faces", {"mode": "minute"}, make_context("1234567", seed=1))
    second: Artifact = build("clock-faces", {"mode": "minute"}, make_context("1234567", seed=2))
    assert first.solver_text != second.solver_text
    assert first == build("clock-faces", {"mode": "minute"}, make_context("1234567", seed=1))


@pytest.mark.parametrize("mode", ["hour", "minute"])
def test_clock_faces_round_trip_reads_the_digits_back(mode: str) -> None:
    context: MechanicContext = make_context("0427")
    params: dict[str, Any] = {"mode": mode}
    assert decode_clocks(build("clock-faces", params, context), params, context) == "0427"


def test_clock_faces_rejects_an_unknown_mode() -> None:
    assert "mode" in build_error("clock-faces", {"mode": "second"}, make_context("12")).message
