import pytest

from mystery_forge.mechanics import freeform, registry
from mystery_forge.mechanics.base import Artifact, MechanicContext, parse_params

FREEFORM_IDS: tuple[str, ...] = ("riddle", "rebus", "deduction", "observation")


def make_context() -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer="Faro", language="es", seed=3, documents={})


@pytest.mark.parametrize("mechanic_id", FREEFORM_IDS)
def test_freeform_mechanics_are_registered_without_a_decoder(mechanic_id: str) -> None:
    implementation = registry.all_implementations()[mechanic_id]
    assert implementation.decode_rendered is None
    assert implementation in freeform.IMPLEMENTATIONS


@pytest.mark.parametrize("mechanic_id", FREEFORM_IDS)
def test_freeform_mechanics_build_no_material(mechanic_id: str) -> None:
    implementation = registry.all_implementations()[mechanic_id]
    params = parse_params(implementation, {"notes": "The answer is in the poem."})
    artifact: Artifact = implementation.build(params, make_context())
    assert artifact.html == ""
    assert artifact.solver_text == ""
    assert artifact.print_notes == ()


def test_freeform_params_default_to_empty_notes() -> None:
    params = parse_params(registry.all_implementations()["riddle"], {})
    assert isinstance(params, freeform.FreeformParams)
    assert params.notes == ""
