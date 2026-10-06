"""The catalog: puzzle mechanics, story ingredients, evidence types, and the design guide, as package data."""

from mystery_forge.catalog.loader import (
    design_rules_text,
    load_evidence_types,
    load_ingredients,
    load_mechanics,
    mechanic_by_id,
)
from mystery_forge.catalog.models import EvidenceType, Ingredients, Mechanic

__all__ = [
    "EvidenceType",
    "Ingredients",
    "Mechanic",
    "design_rules_text",
    "load_evidence_types",
    "load_ingredients",
    "load_mechanics",
    "mechanic_by_id",
]
