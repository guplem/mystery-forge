"""The registry of implemented mechanics, by catalog id."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from mystery_forge.catalog.loader import load_mechanics
from mystery_forge.mechanics import (
    ciphers,
    documents,
    freeform,
    grids,
    logic_grid,
    maze,
    nonogram,
    numbers,
    symbols,
    wordplay,
)
from mystery_forge.mechanics.base import Artifact, MechanicContext, MechanicImplementation

MODULES = (ciphers, symbols, wordplay, numbers, grids, maze, nonogram, logic_grid, documents, freeform)


class PanelOnlyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = ""


def build_nothing(params: PanelOnlyParams, context: MechanicContext) -> Artifact:
    return Artifact(html="", solver_text="")


def all_implementations() -> dict[str, MechanicImplementation[Any]]:
    """Return every implemented mechanic by id. Two modules that claim the same id are a programming error.

    A catalog mechanic that only the solver panel can check needs no code: the agent writes all of its material in
    documents. It gets an implementation that builds nothing, unless a module implements it explicitly.
    """
    implementations: dict[str, MechanicImplementation[Any]] = {}
    for module in MODULES:
        for implementation in module.IMPLEMENTATIONS:
            if implementation.id in implementations:
                raise ValueError(f"Mechanic id '{implementation.id}' is implemented twice.")
            implementations[implementation.id] = implementation
    for mechanic in load_mechanics():
        if mechanic.verification == "panel" and mechanic.id not in implementations:
            implementations[mechanic.id] = MechanicImplementation(
                id=mechanic.id, params_model=PanelOnlyParams, build=build_nothing
            )
    return implementations


def implementation_for(mechanic_id: str) -> MechanicImplementation[Any] | None:
    """Return the implementation of a mechanic, or None when the catalog lists it but no code builds it."""
    return all_implementations().get(mechanic_id)
