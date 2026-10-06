import pytest
from pydantic import BaseModel, ValidationError

from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)


class ShiftParams(BaseModel):
    shift: int


def build_nothing(params: ShiftParams, context: MechanicContext) -> Artifact:
    return Artifact(html="<p>x</p>", solver_text="x")


def test_parse_params_converts_text_values_to_the_declared_types() -> None:
    implementation: MechanicImplementation[ShiftParams] = MechanicImplementation(
        id="demo", params_model=ShiftParams, build=build_nothing
    )
    params: ShiftParams = parse_params(implementation, {"shift": "3"})
    assert params.shift == 3


def test_parse_params_turns_validation_errors_into_a_build_error_with_the_field_path() -> None:
    implementation: MechanicImplementation[ShiftParams] = MechanicImplementation(
        id="demo", params_model=ShiftParams, build=build_nothing
    )
    with pytest.raises(MechanicBuildError) as raised:
        parse_params(implementation, {"shift": "three"})
    assert "shift" in raised.value.message
    assert raised.value.fix_hint


def test_artifact_and_context_are_frozen() -> None:
    artifact = Artifact(html="<b>a</b>", solver_text="a")
    with pytest.raises(ValidationError):
        artifact.html = "changed"  # type: ignore[misc]
    context = MechanicContext(puzzle_id="P1", answer="Faro", language="es", seed=7, documents={})
    assert context.normalized_answer == "faro"
    rendered = RenderedArtifact(text="abc", html="<div>abc</div>")
    assert rendered.text == "abc"


def test_build_error_str_contains_message_and_hint() -> None:
    error = MechanicBuildError("bad shift", fix_hint="use 1 to 25")
    assert str(error) == "bad shift (fix: use 1 to 25)"
