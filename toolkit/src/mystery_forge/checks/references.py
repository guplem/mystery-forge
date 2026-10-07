"""Free-text references: "envelope B" or "page 3" written by hand instead of a `{{stage:B}}` or `{{doc:D3}}` directive.

A directive prints the real envelope label or document title, so it stays right when a stage or a document moves.
The check reads the resolved text, where `{{stage:B}}` already reads "Envelope B". That exact label of an existing
stage therefore passes, and only other forms ("envelope B", "Envelope G") count as free text.

Internal ids (P3, D12) are worse: players never see them, because the print shows codes (A1, B2) and titles.
"""

import re
from dataclasses import dataclass
from typing import Final, Literal

from mystery_forge.checks.game_index import FLOW_FILE, STORY_FILE
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.i18n import text
from mystery_forge.spec.models import Deduction

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

INTERNAL_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b[PD]\d{1,3}\b")


@dataclass(frozen=True)
class PlayerText:
    """A text that players read, with the file and the field path that define it."""

    text: str
    file: str
    path: str | None


def check_references(game: Game) -> list[Finding]:
    return [*free_text_findings(game), *internal_id_findings(game)]


def free_text_findings(game: Game) -> list[Finding]:
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


def without_built_material(document_text: str, game: Game) -> str:
    """Cut the builder output out of a document text: code wrote it, so the writer cannot fix an id in it."""
    for puzzle in game.puzzles:
        if puzzle.artifact is not None and puzzle.artifact.solver_text:
            document_text = document_text.replace(puzzle.artifact.solver_text, "")
    return document_text


def player_texts(game: Game) -> list[PlayerText]:
    texts: list[PlayerText] = [
        PlayerText(without_built_material(document.text, game), document.file, None) for document in game.documents
    ]
    for puzzle in game.puzzles:
        source = puzzle.source
        texts.extend(
            PlayerText(hint.text, puzzle.file, f"hints.{index}.text") for index, hint in enumerate(source.hints)
        )
        texts.extend(
            PlayerText(near_miss.message, puzzle.file, f"near_misses.{index}.message")
            for index, near_miss in enumerate(source.near_misses)
        )
        texts.extend(
            PlayerText(step.text, puzzle.file, f"solution.{index}.text") for index, step in enumerate(source.solution)
        )
    texts.append(PlayerText(game.story.intro, STORY_FILE, "intro"))
    deduction: Deduction | None = game.story.deduction
    for index, question in enumerate(deduction.questions if deduction is not None else []):
        path: str = f"deduction.questions.{index}"
        texts.append(PlayerText(question.prompt, STORY_FILE, f"{path}.prompt"))
        texts.extend(
            PlayerText(option.text, STORY_FILE, f"{path}.options.{position}.text")
            for position, option in enumerate(question.options)
        )
    for index, epilogue in enumerate(game.story.epilogues):
        texts.append(PlayerText(epilogue.title, STORY_FILE, f"epilogues.{index}.title"))
        texts.append(PlayerText(epilogue.text, STORY_FILE, f"epilogues.{index}.text"))
    texts.extend(
        PlayerText(step.text, STORY_FILE, f"reveal.{index}.text") for index, step in enumerate(game.story.reveal)
    )
    texts.extend(
        PlayerText(stage.opening_text, FLOW_FILE, f"stages.{index}.opening_text")
        for index, stage in enumerate(game.flow.stages)
    )
    return texts


def internal_id_findings(game: Game) -> list[Finding]:
    findings: list[Finding] = []
    for player_text in player_texts(game):
        found: list[str] = INTERNAL_ID_PATTERN.findall(player_text.text)
        if not found:
            continue
        findings.append(
            Finding(
                severity="error",
                rule="references.internal_id",
                message=f"A text that players read names the internal ids {', '.join(dict.fromkeys(found))}, which "
                "no printed page shows.",
                file=player_text.file,
                path=player_text.path,
                fix_hint="Name the printed puzzle code (A1, B2) or the document title instead, or write "
                "{{doc:<document id>}} in a document.",
            )
        )
    return findings
