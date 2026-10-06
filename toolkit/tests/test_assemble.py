import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from mystery_forge.assemble import assemble_game, game_salt, puzzle_codes
from mystery_forge.findings import Finding
from mystery_forge.mechanics.base import Artifact, MechanicBuildError, MechanicContext, MechanicImplementation
from mystery_forge.spec.documents import ARTIFACT_MARK

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


class ShiftParams(BaseModel):
    shift: int = 3
    plaintext: str = ""


def build_fake_cipher(params: ShiftParams, context: MechanicContext) -> Artifact:
    if params.shift == 0:
        raise MechanicBuildError("shift 0 hides nothing", fix_hint="use a shift from 1 to 25")
    return Artifact(html="<p class='mf-cipher'>NHBV</p>", solver_text=f"CIPHER<{context.puzzle_id}>")


class LockParams(BaseModel):
    digits: int = 4
    steps: list[dict[str, Any]] = []
    expression: str = ""


def build_fake_lock(params: LockParams, context: MechanicContext) -> Artifact:
    assert "Lamp oil: 7 barrels" in context.documents["D3"]
    return Artifact(html="<svg></svg>", solver_text="A lock with 4 dials.")


class NoParams(BaseModel):
    notes: str = ""


def build_nothing(params: NoParams, context: MechanicContext) -> Artifact:
    return Artifact(html="", solver_text="")


FAKE_IMPLEMENTATIONS: dict[str, MechanicImplementation[Any]] = {
    "caesar-cipher": MechanicImplementation(id="caesar-cipher", params_model=ShiftParams, build=build_fake_cipher),
    "arithmetic-lock": MechanicImplementation(id="arithmetic-lock", params_model=LockParams, build=build_fake_lock),
    "deduction": MechanicImplementation(id="deduction", params_model=NoParams, build=build_nothing),
}


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "source")
    return tmp_path


def rules(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


def test_the_golden_game_assembles(game_dir: Path) -> None:
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert result.findings == []
    game = result.game
    assert game is not None
    assert game.config.language == "en"
    assert game.brief.puzzle_count == 3
    assert [puzzle.code for puzzle in game.puzzles] == ["A1", "A2", "B1"]
    assert game.puzzles[0].artifact is not None
    assert game.puzzles[0].artifact.solver_text == "CIPHER<P1>"
    assert game.puzzles[2].accepted_normalized == ["lowtide", "atlowtide"]
    logbook = game.documents[1]
    assert logbook.meta.id == "D2"
    assert "CIPHER<P1>" in logbook.text
    assert ARTIFACT_MARK.format(puzzle="P1") in logbook.body_html
    assert game.documents[0].text.startswith("Dear friends,")
    assert "Ana Ruiz, Felix Ward, and Maud Price" in game.documents[0].text
    assert len(game.salt) == 16


def test_assemble_writes_nothing_and_reports_a_missing_source(tmp_path: Path) -> None:
    result = assemble_game(tmp_path, FAKE_IMPLEMENTATIONS)
    assert result.game is None
    assert "source.missing" in rules(result.findings)


def test_a_missing_or_invalid_config_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "config.json").unlink()
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert result.game is None
    assert rules(result.findings) == ["source.missing"]
    (game_dir / "source" / "config.json").write_text('{"schema_version": 1, "players": {"count": 99}}', "utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert result.game is None
    assert rules(result.findings) == ["config.maximum"]
    assert result.findings[0].file == "config.json"


def test_a_missing_or_invalid_brief_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "brief.json").unlink()
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert rules(result.findings) == ["source.missing"]
    (game_dir / "source" / "brief.json").write_text("{not json", "utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert rules(result.findings) == ["brief.invalid"]


def test_an_unknown_mechanic_is_reported_on_the_puzzle_file(game_dir: Path) -> None:
    implementations = {key: value for key, value in FAKE_IMPLEMENTATIONS.items() if key != "caesar-cipher"}
    result = assemble_game(game_dir, implementations)
    assert rules(result.findings) == ["mechanic.unknown"]
    assert result.findings[0].file == "puzzles/P1.yaml"
    assert result.game is not None
    assert result.game.puzzles[0].artifact is None


def test_bad_params_and_build_errors_are_reported(game_dir: Path) -> None:
    path = game_dir / "source" / "puzzles" / "P1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("shift: 3", "shift: zero"), "utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert rules(result.findings) == ["mechanic.params"]
    path.write_text(path.read_text(encoding="utf-8").replace("shift: zero", "shift: 0"), "utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert rules(result.findings) == ["mechanic.build"]
    assert result.findings[0].fix_hint == "use a shift from 1 to 25"


def test_reference_and_directive_errors_carry_the_document_file(game_dir: Path) -> None:
    path = game_dir / "source" / "documents" / "D1.md"
    text = path.read_text(encoding="utf-8").replace("{{char:tom-bell}}", "{{char:tom-bel}}")
    path.write_text(text + "\n::: glitter\nx\n:::\n", "utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert rules(result.findings) == ["reference.unknown", "document.unknown_directive"]
    assert {finding.file for finding in result.findings} == {"documents/D1.md"}


def test_an_image_mark_becomes_a_caption_in_the_text(game_dir: Path) -> None:
    images = game_dir / "source" / "images"
    images.mkdir(exist_ok=True)
    (images / "lamp.svg").write_text("<svg></svg>", encoding="utf-8")
    path = game_dir / "source" / "documents" / "D5.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n{{image:lamp|The lamp room}}\n", "utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert result.findings == []
    assert result.game is not None
    assert "[Image: The lamp room]" in result.game.documents[4].text
    assert result.game.images == {"lamp": "<svg></svg>"}


def test_assemble_stops_when_the_story_or_flow_is_broken(game_dir: Path) -> None:
    (game_dir / "source" / "flow.yaml").write_text("format_version: 1\n", encoding="utf-8")
    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert result.game is None
    assert "schema.missing" in rules(result.findings)


def test_puzzle_codes_number_the_puzzles_inside_each_stage() -> None:
    assert puzzle_codes([("P1", "A"), ("P4", "B"), ("P2", "A"), ("P10", "A")]) == {
        "P1": "A1",
        "P2": "A2",
        "P10": "A3",
        "P4": "B1",
    }


def test_game_salt_is_stable_and_depends_on_title_and_seed() -> None:
    assert game_salt("Title", 1) == game_salt("Title", 1)
    assert game_salt("Title", 1) != game_salt("Title", 2)
    assert game_salt("Title", 1) != game_salt("Other", 1)


def test_the_game_json_round_trips(game_dir: Path) -> None:
    from mystery_forge.game import Game

    result = assemble_game(game_dir, FAKE_IMPLEMENTATIONS)
    assert result.game is not None
    dumped = json.loads(result.game.model_dump_json())
    assert Game.model_validate(dumped) == result.game
