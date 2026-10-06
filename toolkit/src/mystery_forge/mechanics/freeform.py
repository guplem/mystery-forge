"""Mechanics that build no material: riddle, rebus, deduction, and observation.

The agent writes these puzzles inside the documents, and only a reader can check them, so the AI solver panel verifies
them (see `adr/0004-verification-strategy.md`).
"""

from typing import Any

from pydantic import BaseModel, Field

from mystery_forge.mechanics.base import Artifact, MechanicContext, MechanicImplementation


class FreeformParams(BaseModel):
    notes: str = Field(default="", description="Free notes for the puzzle writer. The builder ignores them.")


def build_no_material(params: FreeformParams, context: MechanicContext) -> Artifact:
    return Artifact(html="", solver_text="")


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = tuple(
    MechanicImplementation(id=mechanic_id, params_model=FreeformParams, build=build_no_material)
    for mechanic_id in ("riddle", "rebus", "deduction", "observation")
)
