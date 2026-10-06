"""Free-text references: "envelope B" or "page 3" written by hand instead of a `{{stage:B}}` or `{{doc:D3}}` directive.

A directive prints the real envelope label or document title, so it stays right when a stage or a document moves.
The check reads the resolved text, where `{{stage:B}}` already reads "Envelope B". That exact label of an existing
stage therefore passes, and only other forms ("envelope B", "Envelope G") count as free text.
"""

import re
from dataclasses import dataclass
from typing import Final, Literal

from mystery_forge.findings import Finding
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.i18n import text

Directive = Literal["stage", "doc"]


@dataclass(frozen=True)
class FreeTextPattern:
    pattern: re.Pattern[str]
    directive: Directive


def free_text_patterns(envelope: str, page: str, document: str) -> tuple[FreeTextPattern, ...]:
    """Build the patterns of one language from its words for envelope, page, and document."""
    return (
        FreeTextPattern(re.compile(rf"\b(?i:{envelope})\s+([A-H])\b"), "stage"),
        FreeTextPattern(re.compile(rf"\b(?i:{page})\s+\d+\b"), "doc"),
        FreeTextPattern(re.compile(rf"\b(?i:{document})\s+D?\d+\b"), "doc"),
    )


FREE_TEXT_PATTERNS: Final[dict[str, tuple[FreeTextPattern, ...]]] = {
    "en": free_text_patterns("envelope", "page", "document"),
    "es": free_text_patterns("sobre", "página", "documento"),
    "ca": free_text_patterns("sobre", "pàgina", "document"),
    "fr": free_text_patterns("enveloppe", "page", "document"),
    "de": free_text_patterns("umschlag", "seite", "dokument"),
    "it": free_text_patterns("busta", "pagina", "documento"),
    "pt": free_text_patterns("envelope", "página", "documento"),
}


def check_references(game: Game) -> list[Finding]:
    language: str = game.config.language
    stage_labels: set[str] = {text(language, "envelope_label", stage=stage.id) for stage in game.flow.stages}
    findings: list[Finding] = []
    for document in game.documents:
        for free_text in FREE_TEXT_PATTERNS[language]:
            findings.extend(
                free_text_finding(document, match, free_text.directive)
                for match in free_text.pattern.finditer(document.text)
                if match.group(0) not in stage_labels
            )
    return findings


def free_text_finding(document: AssembledDocument, match: re.Match[str], directive: Directive) -> Finding:
    replacement: str = f"{{{{stage:{match.group(1)}}}}}" if directive == "stage" else "{{doc:<document id>}}"
    return Finding(
        severity="warning",
        rule="references.free_text",
        message=f"The document {document.meta.id} writes '{match.group(0)}' as plain text.",
        file=document.file,
        fix_hint=f"Write {replacement} instead, so the text always matches the printed envelope or document.",
    )
