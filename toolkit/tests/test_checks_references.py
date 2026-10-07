from typing import Any

import pytest
from test_checks_support import edit_document, edit_flow, edit_puzzle, edit_story, golden_game, only_rule, rules

from mystery_forge.checks.references import FREE_TEXT_PATTERNS, check_references
from mystery_forge.game import Game
from mystery_forge.spec.models import Deduction, Hint, NearMiss, SolutionStep


def with_text(text: str, language: str = "en") -> Game:
    game: Game = edit_document(golden_game(), "D1", text=text)
    return game.model_copy(update={"config": game.config.model_copy(update={"language": language})})


def test_the_golden_documents_use_directives() -> None:
    assert check_references(golden_game()) == []


def test_free_text_references_are_warnings_with_the_directive_to_use() -> None:
    findings = check_references(with_text("Open envelope B now. See page 4 and document 2."))
    assert rules(findings) == ["references.free_text"] * 3
    assert [finding.file for finding in findings] == ["documents/D1.md"] * 3
    assert {finding.severity for finding in findings} == {"warning"}
    assert "{{stage:B}}" in (findings[0].fix_hint or "")
    assert "{{doc:" in (findings[1].fix_hint or "")


def test_the_exact_text_of_a_stage_directive_is_not_reported() -> None:
    assert check_references(with_text("Now open Envelope B.")) == []
    assert rules(check_references(with_text("Now open Envelope G."))) == ["references.free_text"]


@pytest.mark.parametrize(
    ("language", "text", "count"),
    [
        ("es", "Abre el sobre C y lee la página 3 del documento 2. Sobre B.", 3),
        ("ca", "Obre el sobre C i la pàgina 3.", 2),
        ("fr", "Ouvrez l'enveloppe C, page 3.", 2),
        ("de", "Öffnet Umschlag C und lest Seite 3 im Dokument 1.", 3),
        ("it", "Aprite la busta C a pagina 3.", 2),
        ("pt", "Abram o envelope C na página 3.", 2),
    ],
)
def test_each_language_has_its_own_words(language: str, text: str, count: int) -> None:
    assert len(check_references(with_text(text, language))) == count


def test_every_language_with_a_checked_table_has_patterns() -> None:
    assert set(FREE_TEXT_PATTERNS) == {"en", "es", "ca", "fr", "de", "it", "pt"}


def test_a_language_without_patterns_reports_no_free_text() -> None:
    assert check_references(with_text("Open envelope B.", "ja")) == []


def golden_deduction() -> Deduction:
    deduction: Deduction | None = golden_game().story.deduction
    assert deduction is not None
    return deduction


def internal_id_places(game: Game) -> list[tuple[str | None, str | None]]:
    findings = only_rule(check_references(game), "references.internal_id")
    assert all(finding.severity == "error" and "A1" in (finding.fix_hint or "") for finding in findings)
    return [(finding.file, finding.path) for finding in findings]


def test_an_internal_id_in_a_document_is_an_error() -> None:
    assert internal_id_places(golden_game()) == []
    assert internal_id_places(with_text("Solve P3 first, then read D12.")) == [("documents/D1.md", None)]
    assert internal_id_places(with_text("Flat 3P and DP12 and P1234 are fine.")) == []


def test_an_internal_id_in_a_puzzle_text_is_an_error() -> None:
    game: Game = edit_puzzle(
        golden_game(),
        "P1",
        hints=[Hint(level=1, text="Read D2 again.")],
        near_misses=[NearMiss(answer="boat", message="Close: P1 wants the whole word.")],
        solution=[SolutionStep(text="Decode the line of D2.")],
    )
    assert internal_id_places(game) == [
        ("puzzles/P1.yaml", "hints.0.text"),
        ("puzzles/P1.yaml", "near_misses.0.message"),
        ("puzzles/P1.yaml", "solution.0.text"),
    ]


def test_an_internal_id_in_a_story_or_flow_text_is_an_error() -> None:
    who = golden_deduction().questions[0]
    options: list[Any] = [who.options[0].model_copy(update={"text": "The cook of D1"}), *who.options[1:]]
    question = who.model_copy(update={"prompt": "Who solved P2?", "options": options})
    game: Game = edit_story(
        golden_game(),
        intro="Start with D1.",
        deduction=golden_deduction().model_copy(update={"questions": [question]}),
        epilogues=[golden_game().story.epilogues[0].model_copy(update={"title": "P3 solved", "text": "See D5."})],
        reveal=[golden_game().story.reveal[0].model_copy(update={"text": "As D4 shows."})],
    )
    stages = [golden_game().flow.stages[0], golden_game().flow.stages[1].model_copy(update={"opening_text": "Do P3."})]
    game = edit_flow(game, stages=stages)
    assert internal_id_places(game) == [
        ("story.yaml", "intro"),
        ("story.yaml", "deduction.questions.0.prompt"),
        ("story.yaml", "deduction.questions.0.options.0.text"),
        ("story.yaml", "epilogues.0.title"),
        ("story.yaml", "epilogues.0.text"),
        ("story.yaml", "reveal.0.text"),
        ("flow.yaml", "stages.1.opening_text"),
    ]
    no_deduction: Game = edit_story(golden_game(), deduction=None)
    assert internal_id_places(no_deduction) == []
