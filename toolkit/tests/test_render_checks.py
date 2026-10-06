import re
import shutil
from pathlib import Path

import pytest

from mystery_forge.assemble import assemble_game
from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.mechanics.base import RenderedArtifact
from mystery_forge.mechanics.registry import all_implementations
from mystery_forge.render.game_renderer import RenderedOutput, RenderReport
from mystery_forge.render_checks import check_rendered

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


@pytest.fixture(scope="module")
def game(tmp_path_factory: pytest.TempPathFactory) -> Game:
    game_dir = tmp_path_factory.mktemp("game")
    shutil.copytree(GOLDEN_GAME / "source", game_dir / "source")
    result = assemble_game(game_dir)
    assert result.game is not None
    return result.game


def rendered(html: str) -> RenderedArtifact:
    return RenderedArtifact(text=re.sub(r"<[^>]+>", " ", html), html=html)


def report(
    game: Game, artifacts: dict[str, RenderedArtifact], texts: list[str], stages: list[str | None], roles: list[str]
) -> RenderReport:
    materials = RenderedOutput(
        id="materials",
        html_file=Path("materials.html"),
        pdf_file=None,
        sheet_count=len(texts),
        sheet_roles=roles,
        sheet_stages=stages,
        sheet_texts=texts,
    )
    return RenderReport(
        theme="vintage", files=[], outputs={"materials": materials}, findings=[], artifacts=artifacts, previews=[]
    )


def golden_artifacts(game: Game) -> dict[str, RenderedArtifact]:
    return {
        puzzle.source.id: rendered(puzzle.artifact.html)
        for puzzle in game.puzzles
        if puzzle.artifact is not None and puzzle.artifact.html
    }


def rules(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


def test_the_golden_render_passes(game: Game) -> None:
    clean = report(game, golden_artifacts(game), ["Welcome", "A letter"], [None, "A"], ["cover", "document"])
    assert check_rendered(game, clean, all_implementations()) == []


def test_a_changed_letter_in_the_printed_cipher_fails_the_roundtrip(game: Game) -> None:
    artifacts = golden_artifacts(game)
    html = artifacts["P1"].html.replace("ERDWKRXVH", "ERDWKRXVJ")
    artifacts["P1"] = rendered(html)
    findings = check_rendered(game, report(game, artifacts, [], [], []), all_implementations())
    assert rules(findings) == ["render.roundtrip"]
    assert findings[0].file == "puzzles/P1.yaml"


def test_a_missing_artifact_is_reported(game: Game) -> None:
    artifacts = golden_artifacts(game)
    del artifacts["P1"]
    findings = check_rendered(game, report(game, artifacts, [], [], []), all_implementations())
    assert rules(findings) == ["render.artifact_missing"]


def test_an_answer_on_an_early_page_is_a_leak(game: Game) -> None:
    texts = ["The code is 0726", "Low tide: 1:50 in the night", "boathouse key"]
    leaky = report(game, golden_artifacts(game), texts, [None, "B", "B"], ["cover", "document", "document"])
    assert rules(check_rendered(game, leaky, all_implementations())) == ["render.leak"]


def test_register_pages_and_later_stages_are_not_leaks(game: Game) -> None:
    texts = ["0726 boathouse low tide", "boathouse"]
    safe = report(game, golden_artifacts(game), texts, [None, "B"], ["register", "document"])
    assert check_rendered(game, safe, all_implementations()) == []


def test_an_allowlisted_text_is_not_a_leak(game: Game) -> None:
    texts = ["Low tide: 1:50 in the night"]
    allowed = report(game, golden_artifacts(game), texts, ["B"], ["document"])
    assert check_rendered(game, allowed, all_implementations()) == []


def test_no_materials_output_means_no_leak_check(game: Game) -> None:
    empty = RenderReport(
        theme="vintage", files=[], outputs={}, findings=[], artifacts=golden_artifacts(game), previews=[]
    )
    assert check_rendered(game, empty, all_implementations()) == []


def test_unknown_mechanics_and_artifacts_without_a_decoder_are_skipped(game: Game) -> None:
    implementations = dict(all_implementations())
    del implementations["caesar-cipher"]
    findings = check_rendered(game, report(game, {}, [], [], []), implementations)
    assert rules(findings) == ["render.artifact_missing"]


def test_name_answers_are_not_leak_checked(game: Game) -> None:
    first = game.puzzles[0]
    named_format = first.source.answer_format.model_copy(update={"kind": "name"})
    named = first.model_copy(update={"source": first.source.model_copy(update={"answer_format": named_format})})
    named_game = game.model_copy(update={"puzzles": [named]})
    texts = ["the boathouse"]
    leaky = report(named_game, golden_artifacts(named_game), texts, [None], ["document"])
    assert check_rendered(named_game, leaky, all_implementations()) == []
