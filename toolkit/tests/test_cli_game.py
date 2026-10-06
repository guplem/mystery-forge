import io
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from mystery_forge import cli
from mystery_forge.paths import SystemFolders

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


def run(argv: list[str], stdin: str | None = None, monkeypatch: pytest.MonkeyPatch | None = None) -> Any:
    if stdin is not None and monkeypatch is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    output = io.StringIO()
    assert cli.main(argv, output) == 0
    return json.loads(output.getvalue())


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "game" / "source")
    return tmp_path / "game"


def golden_plan() -> dict[str, Any]:
    return {
        "format_version": 1,
        "motif": "The tide table returns.",
        "puzzles": [
            {"id": "P1", "stage": "A", "title": "Coded line", "mechanic": "caesar-cipher", "difficulty": "easy",
             "answer": "boathouse", "in_world_reason": "Hidden notes.", "reveals": "Keys.", "documents": ["D2"]},
            {"id": "P2", "stage": "A", "title": "The lock", "mechanic": "arithmetic-lock", "difficulty": "easy",
             "answer": "0726", "in_world_reason": "A lock.", "reveals": "Rope.", "documents": ["D3"]},
            {"id": "P3", "stage": "B", "title": "The tide", "mechanic": "deduction", "difficulty": "medium",
             "depends_on": ["P1"], "answer": "low tide", "in_world_reason": "A causeway.", "reveals": "Low tide.",
             "documents": ["D4"]},
        ],
        "story_documents": [
            {"id": "D1", "kind": "letter", "stage": "A", "title": "A letter", "purpose": "Sets the case."},
            {"id": "D5", "kind": "generic", "stage": "B", "title": "Two papers", "purpose": "Clears Maud."},
        ],
    }  # fmt: skip


def write_plan(game_dir: Path) -> None:
    (game_dir / "source" / "plan.yaml").write_text(yaml.safe_dump(golden_plan()), encoding="utf-8")


def test_check_story_plan_and_full(game_dir: Path) -> None:
    story = run(["check", "--game", str(game_dir), "--scope", "story"])
    assert story["ok"] is True
    assert story["fix_groups"] == []
    write_plan(game_dir)
    plan = run(["check", "--game", str(game_dir), "--scope", "plan"])
    assert plan["ok"] is True
    full = run(["check", "--game", str(game_dir), "--scope", "full"])
    assert full["ok"] is True
    assert (game_dir / "game.json").is_file()
    assert (game_dir / "reports" / "verification.json").is_file()


def test_check_groups_the_errors_for_the_fixers(game_dir: Path) -> None:
    path = game_dir / "source" / "puzzles" / "P1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("my code goes back three steps", "no such words"), "utf-8")
    result = run(["check", "--game", str(game_dir)])
    assert result["ok"] is False
    assert [group["name"] for group in result["fix_groups"]] == ["P1"]
    assert Path(result["fix_groups"][0]["findings_file"]).is_file()


def test_check_full_on_a_broken_story_reports_without_a_game(game_dir: Path) -> None:
    (game_dir / "source" / "story.yaml").write_text("format_version: 1\n", encoding="utf-8")
    result = run(["check", "--game", str(game_dir)])
    assert result["ok"] is False
    assert not (game_dir / "game.json").exists()


def test_writer_tasks_list_the_planned_puzzles(game_dir: Path) -> None:
    missing = run(["writer-tasks", "--game", str(game_dir)])
    assert missing["ok"] is False
    write_plan(game_dir)
    result = run(["writer-tasks", "--game", str(game_dir)])
    assert [task["name"] for task in result["tasks"]] == ["P1 caesar-cipher", "P2 arithmetic-lock", "P3 deduction"]
    assert result["tasks"][2]["documents"] == ["D4"]


def solver_answers(stage: str) -> list[dict[str, Any]]:
    if stage == "A":
        return [
            {"code": "A1", "answer": "boathouse", "stuck": False, "reasoning": "Back three.", "candidates": [],
             "evidence": [{"document": "The keeper's logbook", "quote": "my code goes back three steps"}]},
            {"code": "A2", "answer": "0726", "stuck": False, "reasoning": "Receipt.", "candidates": [],
             "evidence": [{"document": "The supply receipt", "quote": "Lamp oil: 7 barrels"}]},
        ]  # fmt: skip
    return [
        {"code": "B1", "answer": "low tide", "stuck": False, "reasoning": "Tide table.", "candidates": [],
         "evidence": [{"document": "Notes from the boathouse box", "quote": "Low tide: 1:50 in the night"}]},
    ]  # fmt: skip


def accusation(stage: str) -> list[dict[str, Any]]:
    if stage != "B":
        return []
    evidence = [{"document": "Two papers from the box", "quote": "Mr Ward still owes me forty pounds"}]
    return [
        {"question": "who", "option": "felix", "evidence": evidence},
        {"question": "why", "option": "debt", "evidence": evidence},
    ]


def test_packets_judge_status_render_and_export(
    game_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_plan(game_dir)
    assert run(["check", "--game", str(game_dir)])["ok"] is True
    packets = run(["packets", "--game", str(game_dir)])
    assert packets["ok"] is True
    tasks = packets["solver_tasks"]
    assert len(tasks) == 2 * 5
    assert Path(tasks[0]["packet_file"]).read_text(encoding="utf-8").strip()
    assert Path(packets["guesser_file"]).is_file()
    results = [
        {"status": "done", "answers": solver_answers(task["stage"]), "accusation": accusation(task["stage"])}
        for task in tasks
    ]
    payload = {"solver_tasks": tasks, "solver_results": results, "guesser_result": {"guesses": []}}
    judged = run(["judge", "--game", str(game_dir)], json.dumps(payload), monkeypatch)
    assert judged["ok"] is True, judged
    assert judged["failing_items"] == []
    assert run(["status", "--game", str(game_dir)])["ok"] is True
    rendered = run(["render", "--game", str(game_dir), "--html-only"])
    assert rendered["ok"] is True
    assert (game_dir / "render" / "Game companion.html").is_file()
    for name in (
        "1 - START HERE (manual).pdf",
        "2 - PRINT THIS (game materials).pdf",
        "3 - Hints.pdf",
        "4 - Solutions.pdf",
    ):
        (game_dir / "render" / name).write_bytes(b"%PDF")
    exported = run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out")])
    assert exported["ok"] is True
    assert Path(exported["folder"]).name == "The Lens of Gull Rock"


def test_judge_reports_failing_items_with_their_files(game_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_plan(game_dir)
    packets = run(["packets", "--game", str(game_dir)])
    tasks = packets["solver_tasks"]
    codes = {"A": ("A1", "A2"), "B": ("B1",)}

    def stuck(stage: str) -> list[dict[str, Any]]:
        return [
            {"code": code, "answer": "", "stuck": True, "reasoning": "?", "candidates": [], "evidence": []}
            for code in codes[stage]
        ]

    results = [{"status": "done", "answers": stuck(task["stage"]), "accusation": []} for task in tasks]
    payload = {"solver_tasks": tasks, "solver_results": results, "guesser_result": None}
    judged = run(["judge", "--game", str(game_dir), "--input", json.dumps(payload)])
    assert judged["ok"] is False
    by_code = {item["code"]: item for item in judged["failing_items"]}
    assert by_code["A1"]["files"] == ["puzzles/P1.yaml", "documents/D2.md"]
    assert by_code["who"]["files"][0] == "story.yaml"
    notes = json.loads(Path(by_code["A1"]["findings_file"]).read_text(encoding="utf-8"))
    assert notes["verdict"]["verdict"] == "too_hard"
    assert len(notes["solver_answers"]) == 5
    status = run(["status", "--game", str(game_dir), "--panel", "false"])
    assert status["ok"] is False
    assert status["stale"]


def test_verbs_on_a_broken_game_report_findings(game_dir: Path) -> None:
    (game_dir / "source" / "flow.yaml").unlink()
    for verb in ("packets", "status", "export"):
        result = run([verb, "--game", str(game_dir)])
        assert result["ok"] is False
        assert result["errors"] >= 1
    result = run(["render", "--game", str(game_dir), "--html-only"])
    assert [group["name"] for group in result["fix_groups"]] == ["plan"]


def test_export_without_a_render_is_reported(game_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folders = SystemFolders(desktop=tmp_path / "Desktop", downloads=tmp_path / "Downloads")
    monkeypatch.setattr(cli, "find_system_folders", lambda: folders)
    result = run(["export", "--game", str(game_dir)])
    assert result["ok"] is False
    assert "forge render" in result["message"]


@pytest.mark.browser
def test_render_prints_the_pdfs_with_a_browser(game_dir: Path) -> None:
    result = run(["render", "--game", str(game_dir)])
    assert result["ok"] is True, result
    assert (game_dir / "render" / "2 - PRINT THIS (game materials).pdf").is_file()
    assert result["sheets"]["materials"] > 5


def set_config(game_dir: Path, **changes: Any) -> None:
    path = game_dir / "source" / "config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        section, _, field = key.partition("__")
        if field:
            config[section][field] = value
        else:
            config[section] = value
    path.write_text(json.dumps(config), encoding="utf-8")


def test_kids_games_get_a_kids_solver_persona(game_dir: Path) -> None:
    set_config(game_dir, audience="kids")
    packets = run(["packets", "--game", str(game_dir)])
    personas = {task["persona"] for task in packets["solver_tasks"]}
    assert any("10-year-old" in persona for persona in personas)


def test_judge_on_a_broken_game_reports_findings(game_dir: Path) -> None:
    (game_dir / "source" / "flow.yaml").unlink()
    result = run(["judge", "--game", str(game_dir), "--input", "{}"])
    assert result["ok"] is False


def test_render_without_a_companion_page(game_dir: Path) -> None:
    set_config(game_dir, assistance__companion_page=False)
    result = run(["render", "--game", str(game_dir), "--html-only"])
    assert result["ok"] is True
    assert not (game_dir / "render" / "Game companion.html").exists()
