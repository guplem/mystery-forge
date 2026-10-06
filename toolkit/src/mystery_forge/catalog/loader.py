"""Load the catalog files that ship inside the package.

Developers write the catalog files by hand, and every scalar in them is intentional, so `yaml.safe_load` reads them
directly. Each loader caches its result: the files never change while the process runs.
"""

import difflib
from functools import cache
from importlib import resources
from typing import Any

import yaml

from mystery_forge.catalog.models import (
    EvidenceCatalog,
    EvidenceType,
    Ingredients,
    Mechanic,
    MechanicCatalog,
)


def read_catalog_text(file_name: str) -> str:
    return resources.files("mystery_forge.catalog").joinpath(file_name).read_text(encoding="utf-8")


def read_catalog_yaml(file_name: str) -> Any:
    return yaml.safe_load(read_catalog_text(file_name))


@cache
def load_mechanics() -> tuple[Mechanic, ...]:
    return MechanicCatalog.model_validate(read_catalog_yaml("mechanics.yaml")).mechanics


@cache
def load_ingredients() -> Ingredients:
    return Ingredients.model_validate(read_catalog_yaml("ingredients.yaml"))


@cache
def load_evidence_types() -> tuple[EvidenceType, ...]:
    return EvidenceCatalog.model_validate(read_catalog_yaml("evidence.yaml")).evidence_types


@cache
def design_rules_text() -> str:
    """Return the design guide that the agents read before they write a game."""
    return read_catalog_text("design_rules.md")


@cache
def mechanics_by_id() -> dict[str, Mechanic]:
    return {mechanic.id: mechanic for mechanic in load_mechanics()}


def mechanic_by_id(mechanic_id: str) -> Mechanic:
    """Return one mechanic. An unknown id raises KeyError that names the closest known ids."""
    known: dict[str, Mechanic] = mechanics_by_id()
    if mechanic_id in known:
        return known[mechanic_id]
    close_ids: list[str] = difflib.get_close_matches(mechanic_id, known, n=3)
    suggestion: str = (
        f"Did you mean: {', '.join(close_ids)}?" if close_ids else "Run `forge catalog` to list the mechanic ids."
    )
    raise KeyError(f"Unknown mechanic id '{mechanic_id}'. {suggestion}")
