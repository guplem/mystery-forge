from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from mystery_forge.mechanics import registry
from mystery_forge.mechanics.base import Artifact, MechanicContext, MechanicImplementation


class NoParams(BaseModel):
    pass


def build_empty(params: NoParams, context: MechanicContext) -> Artifact:
    return Artifact(html="", solver_text="")


def make_implementation(mechanic_id: str) -> MechanicImplementation[Any]:
    return MechanicImplementation(id=mechanic_id, params_model=NoParams, build=build_empty)


def test_implementation_for_returns_none_for_an_unknown_id() -> None:
    assert registry.implementation_for("no-such-mechanic") is None


def test_all_implementations_rejects_a_duplicate_id(monkeypatch: pytest.MonkeyPatch) -> None:
    first = SimpleNamespace(IMPLEMENTATIONS=(make_implementation("same"),))
    second = SimpleNamespace(IMPLEMENTATIONS=(make_implementation("same"),))
    monkeypatch.setattr(registry, "MODULES", (first, second))
    with pytest.raises(ValueError, match="implemented twice"):
        registry.all_implementations()


def test_all_implementations_collects_every_module(monkeypatch: pytest.MonkeyPatch) -> None:
    first = SimpleNamespace(IMPLEMENTATIONS=(make_implementation("one"),))
    second = SimpleNamespace(IMPLEMENTATIONS=(make_implementation("two"),))
    monkeypatch.setattr(registry, "MODULES", (first, second))
    assert {"one", "two"} <= set(registry.all_implementations())
    assert registry.implementation_for("two") is not None


def test_every_panel_mechanic_of_the_catalog_gets_an_empty_implementation() -> None:
    from mystery_forge.catalog.loader import load_mechanics

    implementations = registry.all_implementations()
    for mechanic in load_mechanics():
        if mechanic.verification == "panel":
            assert mechanic.id in implementations, mechanic.id
    panel_ids = [mechanic.id for mechanic in load_mechanics() if mechanic.verification == "panel"]
    implementation = implementations[panel_ids[-1]]
    params = implementation.params_model.model_validate({"notes": "x"})
    context = MechanicContext(puzzle_id="P1", answer="x", language="en", seed=1, documents={})
    artifact = implementation.build(params, context)
    assert artifact.html == ""
    assert artifact.solver_text == ""
