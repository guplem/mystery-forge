import pytest
from test_checks_support import edit_document, golden_game, rules

from mystery_forge.checks.references import FREE_TEXT_PATTERNS, check_references
from mystery_forge.game import Game


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


def test_every_game_language_has_patterns() -> None:
    assert set(FREE_TEXT_PATTERNS) == {"en", "es", "ca", "fr", "de", "it", "pt"}
