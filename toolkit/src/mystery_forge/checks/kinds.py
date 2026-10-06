"""Document kinds: each document names a kind that the renderer has a template for."""

from typing import Final

from mystery_forge.findings import Finding
from mystery_forge.game import Game

# The renderer (`render/kinds.py`) has one template per kind and must keep this same list. A test compares both.
KNOWN_DOCUMENT_KINDS: Final[tuple[str, ...]] = (
    "letter",
    "notebook",
    "receipt",
    "police-report",
    "newspaper",
    "telegram",
    "transcript",
    "email",
    "chat-log",
    "ticket",
    "id-card",
    "map",
    "photo",
    "poster",
    "form",
    "case-briefing",
    "generic",
)


def check_document_kinds(game: Game) -> list[Finding]:
    return [
        Finding(
            severity="error",
            rule="documents.kind_unknown",
            message=f"The document {document.meta.id} has the kind '{document.meta.kind}', which has no template.",
            file=document.file,
            path="kind",
            fix_hint=f"Use one of: {', '.join(KNOWN_DOCUMENT_KINDS)}.",
        )
        for document in game.documents
        if document.meta.kind not in KNOWN_DOCUMENT_KINDS
    ]
