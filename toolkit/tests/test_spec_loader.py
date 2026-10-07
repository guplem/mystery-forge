import shutil
from pathlib import Path

import pytest

from mystery_forge.findings import Finding
from mystery_forge.spec.loader import GameSource, load_game_source

GOLDEN_SOURCE: Path = Path(__file__).parent / "fixtures" / "golden" / "source"


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    """A writable copy of the golden game, as a game folder with a `source/` folder."""
    shutil.copytree(GOLDEN_SOURCE, tmp_path / "source")
    return tmp_path


def rules(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


def test_the_golden_game_loads_without_findings(game_dir: Path) -> None:
    source, findings = load_game_source(game_dir)
    assert findings == []
    assert isinstance(source, GameSource)
    assert source.story is not None
    assert source.story.title == "The Lens of Gull Rock"
    assert source.flow is not None
    assert [puzzle.id for puzzle in source.puzzles] == ["P1", "P2", "P3"]
    assert [document.meta.id for document in source.documents] == ["D1", "D2", "D3", "D4", "D5"]
    assert source.documents[1].body_line == 11
    assert source.documents[1].file == "documents/D2.md"
    assert source.images == {}


def test_puzzles_and_documents_sort_by_number_not_by_text(game_dir: Path) -> None:
    puzzle_text = (game_dir / "source" / "puzzles" / "P1.yaml").read_text(encoding="utf-8")
    (game_dir / "source" / "puzzles" / "P10.yaml").write_text(puzzle_text.replace("id: P1", "id: P10"), "utf-8")
    source, _ = load_game_source(game_dir)
    assert [puzzle.id for puzzle in source.puzzles] == ["P1", "P2", "P3", "P10"]


def test_a_missing_story_or_flow_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "story.yaml").unlink()
    (game_dir / "source" / "flow.yaml").unlink()
    source, findings = load_game_source(game_dir)
    assert source.story is None
    assert source.flow is None
    assert rules(findings) == ["source.missing", "source.missing"]
    assert findings[0].file == "story.yaml"
    assert findings[0].fix_hint


def test_a_missing_source_folder_is_one_finding(tmp_path: Path) -> None:
    _, findings = load_game_source(tmp_path)
    assert rules(findings) == ["source.missing"]
    assert findings[0].file == "source"


def test_a_yaml_syntax_error_names_the_file_and_line(game_dir: Path) -> None:
    (game_dir / "source" / "flow.yaml").write_text("format_version: 1\nstages: [\n", encoding="utf-8")
    source, findings = load_game_source(game_dir)
    assert source.flow is None
    assert rules(findings) == ["yaml.syntax"]
    assert findings[0].file == "flow.yaml"
    assert findings[0].line is not None


def test_a_validation_error_names_the_field_path_and_its_line(game_dir: Path) -> None:
    path = game_dir / "source" / "puzzles" / "P2.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("difficulty: easy", "difficulty: trivial"), "utf-8")
    source, findings = load_game_source(game_dir)
    assert [puzzle.id for puzzle in source.puzzles] == ["P1", "P3"]
    assert rules(findings) == ["schema.literal_error"]
    assert findings[0].file == "puzzles/P2.yaml"
    assert findings[0].path == "difficulty"
    assert findings[0].line == 6


def test_a_model_rule_error_without_a_field_points_at_the_file(game_dir: Path) -> None:
    path = game_dir / "source" / "flow.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("opens_with: start", "opens_with: P2"), "utf-8")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["schema.value_error"]
    assert findings[0].path == ""
    assert "start" in findings[0].message


def test_a_file_whose_top_level_is_not_a_mapping_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "story.yaml").write_text("- just\n- a list\n", encoding="utf-8")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["schema.not_a_mapping"]


def test_a_puzzle_file_name_must_start_with_its_id(game_dir: Path) -> None:
    source_dir = game_dir / "source" / "puzzles"
    (source_dir / "P2.yaml").rename(source_dir / "P7-lock.yaml")
    source, findings = load_game_source(game_dir)
    assert rules(findings) == ["source.file_name"]
    assert findings[0].file == "puzzles/P7-lock.yaml"
    assert [puzzle.id for puzzle in source.puzzles] == ["P1", "P3"]


def test_a_puzzle_file_with_a_slug_after_the_id_is_fine(game_dir: Path) -> None:
    source_dir = game_dir / "source" / "puzzles"
    (source_dir / "P2.yaml").rename(source_dir / "P2-store-lock.yaml")
    source, findings = load_game_source(game_dir)
    assert findings == []
    assert len(source.puzzles) == 3


def test_a_document_without_front_matter_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "documents" / "D9.md").write_text("Just text\n", encoding="utf-8")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["document.front_matter"]


def test_a_document_with_broken_front_matter_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "documents" / "D9.md").write_text("---\nid: D9\n", encoding="utf-8")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["yaml.syntax"]


def test_a_document_validation_error_uses_the_front_matter_lines(game_dir: Path) -> None:
    path = game_dir / "source" / "documents" / "D3.md"
    path.write_text(path.read_text(encoding="utf-8").replace("stage: A", "stage: Q"), "utf-8")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["schema.string_pattern_mismatch"]
    assert findings[0].line == 5


def test_duplicate_ids_across_files_are_reported(game_dir: Path) -> None:
    source_dir = game_dir / "source" / "documents"
    shutil.copy(source_dir / "D1.md", source_dir / "D1-copy.md")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["source.duplicate_id"]


def test_svg_images_are_read_and_other_files_are_ignored(game_dir: Path) -> None:
    images = game_dir / "source" / "images"
    images.mkdir(exist_ok=True)
    (images / "lamp.svg").write_text("<svg></svg>", encoding="utf-8")
    (images / "notes.txt").write_text("ignored", encoding="utf-8")
    source, findings = load_game_source(game_dir)
    assert findings == []
    assert source.images == {"lamp": "<svg></svg>"}


def test_a_game_without_image_puzzle_or_document_folders_loads(game_dir: Path) -> None:
    for folder in ("images", "puzzles", "documents"):
        shutil.rmtree(game_dir / "source" / folder, ignore_errors=True)
    source, findings = load_game_source(game_dir)
    assert findings == []
    assert source.puzzles == ()
    assert source.documents == ()


def test_unknown_and_missing_fields_get_specific_fix_hints(game_dir: Path) -> None:
    path = game_dir / "source" / "puzzles" / "P1.yaml"
    text = path.read_text(encoding="utf-8").replace("title: ", "titel: ")
    path.write_text(text, encoding="utf-8")
    _, findings = load_game_source(game_dir)
    hints = {finding.rule: finding.fix_hint for finding in findings}
    assert hints["schema.extra_forbidden"] == "Remove this field, or check its spelling against `forge schema`."
    assert hints["schema.missing"] == "Add this required field."


def test_a_control_character_in_a_file_is_a_syntax_finding(game_dir: Path) -> None:
    (game_dir / "source" / "flow.yaml").write_text("format_version: 1\x07\n", encoding="utf-8")
    source, findings = load_game_source(game_dir)
    assert source.flow is None
    assert rules(findings) == ["yaml.syntax"]
    assert findings[0].file == "flow.yaml"


@pytest.mark.parametrize("file", ["story.yaml", "puzzles/P1.yaml", "documents/D1.md", "images/lamp.svg"])
def test_a_file_that_is_not_utf8_is_an_encoding_finding(game_dir: Path, file: str) -> None:
    path = game_dir / "source" / file
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"title: Caf\xe9\n")
    _, findings = load_game_source(game_dir)
    assert rules(findings) == ["source.encoding"]
    assert findings[0].file == file


def test_a_byte_order_mark_before_the_front_matter_is_fine(game_dir: Path) -> None:
    path = game_dir / "source" / "documents" / "D1.md"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    story = game_dir / "source" / "story.yaml"
    story.write_bytes(b"\xef\xbb\xbf" + story.read_bytes())
    _, findings = load_game_source(game_dir)
    assert findings == []


def test_a_puzzle_file_without_a_numbered_name_is_reported(game_dir: Path) -> None:
    source_dir = game_dir / "source" / "puzzles"
    (source_dir / "P3.yaml").rename(source_dir / "notes.yaml")
    source, findings = load_game_source(game_dir)
    assert [finding.rule for finding in findings] == ["source.file_name"]
    assert [puzzle.id for puzzle in source.puzzles] == ["P1", "P2"]
