import json
import shutil
from pathlib import Path

import pytest
import yaml

from mystery_forge.findings import Finding
from mystery_forge.fix_groups import file_owners, group_findings, write_fix_groups

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "source")
    return tmp_path


def finding(file: str | None, rule: str = "x.y") -> Finding:
    return Finding(severity="error", rule=rule, message="m", file=file)


def test_owners_come_from_the_document_front_matter(game_dir: Path) -> None:
    owners = file_owners(game_dir)
    assert owners["documents/D2.md"] == "P1"
    assert owners["documents/D3.md"] == "P2"
    assert owners["documents/D1.md"] == "documents"
    assert owners["puzzles/P3.yaml"] == "P3"


def test_owners_from_the_plan_win_and_cover_files_that_do_not_exist_yet(game_dir: Path) -> None:
    plan = {"puzzles": [{"id": "P1", "documents": ["D2", "D9"]}], "story_documents": [{"id": "D3"}]}
    (game_dir / "source" / "plan.yaml").write_text(yaml.safe_dump(plan), encoding="utf-8")
    owners = file_owners(game_dir)
    assert owners["documents/D9.md"] == "P1"
    assert owners["documents/D3.md"] == "documents"


def test_an_unreadable_plan_or_document_is_ignored(game_dir: Path) -> None:
    (game_dir / "source" / "plan.yaml").write_text("puzzles: [", encoding="utf-8")
    (game_dir / "source" / "documents" / "D8.md").write_text("no front matter", encoding="utf-8")
    (game_dir / "source" / "documents" / "D7.md").write_text("---\nid: D7\n", encoding="utf-8")
    owners = file_owners(game_dir)
    assert "documents/D7.md" not in owners
    assert owners["documents/D2.md"] == "P1"
    assert "documents/D8.md" not in owners


def test_findings_are_grouped_by_the_writer_that_owns_their_file(game_dir: Path) -> None:
    findings = [
        finding("puzzles/P1.yaml"),
        finding("documents/D2.md"),
        finding("documents/D1.md"),
        finding("story.yaml"),
        finding(None),
        finding("flow.yaml"),
        finding("images/lamp.svg"),
        finding("config.json"),
    ]
    groups = {group.name: group for group in group_findings(findings, game_dir)}
    assert sorted(groups) == ["P1", "documents", "plan", "story"]
    assert len(groups["P1"].findings) == 2
    assert groups["P1"].files == ["puzzles/P1.yaml", "documents/D2.md"]
    assert "documents/D1.md" in groups["documents"].files
    assert "images/" in groups["documents"].files
    assert len(groups["story"].findings) == 2
    assert groups["plan"].files == ["plan.yaml", "flow.yaml"]


def test_warnings_alone_make_no_group(game_dir: Path) -> None:
    warning = Finding(severity="warning", rule="x", message="m", file="story.yaml")
    assert group_findings([warning], game_dir) == []


def test_a_group_keeps_its_warnings_next_to_its_errors(game_dir: Path) -> None:
    warning = Finding(severity="warning", rule="w", message="m", file="puzzles/P2.yaml")
    groups = group_findings([finding("puzzles/P2.yaml"), warning], game_dir)
    assert [len(group.findings) for group in groups] == [2]


def test_write_fix_groups_writes_one_findings_file_per_group(game_dir: Path) -> None:
    groups = group_findings([finding("puzzles/P1.yaml"), finding("story.yaml")], game_dir)
    entries = write_fix_groups(groups, game_dir, "full")
    assert [entry["name"] for entry in entries] == ["P1", "story"]
    first = json.loads(Path(entries[0]["findings_file"]).read_text(encoding="utf-8"))
    assert first["findings"][0]["file"] == "puzzles/P1.yaml"
    assert entries[0]["files"] == ["puzzles/P1.yaml", "documents/D2.md"]


def test_findings_on_toolkit_pages_make_no_group(game_dir: Path) -> None:
    assert group_findings([finding("materials.html"), finding("solutions.html")], game_dir) == []


def test_toolkit_overflow_findings_make_no_group(game_dir: Path) -> None:
    toolkit_bug = Finding(severity="error", rule="render.toolkit_overflow", message="m", file=None)
    assert group_findings([toolkit_bug], game_dir) == []
