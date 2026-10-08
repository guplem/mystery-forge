import contextlib
import io
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from mystery_forge import cli
from mystery_forge.paths import SystemFolders
from mystery_forge.render.sheets import OutputFileNames, output_file_names

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
             "answer": "boathouse", "in_world_reason": "Hidden notes.",
             "hidden_from": "the crew", "reveals": "Keys.", "documents": ["D2"]},
            {"id": "P2", "stage": "A", "title": "The lock", "mechanic": "arithmetic-lock", "difficulty": "easy",
             "answer": "0726", "in_world_reason": "A lock.",
             "hidden_from": "the crew", "reveals": "Rope.", "documents": ["D3"],
             "must_contain": ["Lamp oil: 7 barrels"]},
            {"id": "P3", "stage": "B", "title": "The tide", "mechanic": "deduction", "difficulty": "medium",
             "depends_on": ["P1"], "answer": "low tide", "in_world_reason": "A causeway.",
             "hidden_from": "visitors", "reveals": "Low tide.",
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
    assert result["tasks"][1]["must_contain"] == ["Lamp oil: 7 barrels"]
    assert result["tasks"][0]["must_contain"] == []


def test_the_full_check_reports_a_planned_sentence_that_a_document_lost(game_dir: Path) -> None:
    write_plan(game_dir)
    path = game_dir / "source" / "documents" / "D3.md"
    path.write_text(path.read_text(encoding="utf-8").replace("Lamp oil: 7 barrels", "Lamp oil: seven barrels"), "utf-8")
    result = run(["check", "--game", str(game_dir)])
    assert result["ok"] is False
    assert "plan.must_contain_missing" in {finding["rule"] for finding in result["findings"]}
    assert "P2" in [group["name"] for group in result["fix_groups"]]


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
    assert len(tasks) == 3 * 5
    assert Path(tasks[0]["packet_file"]).read_text(encoding="utf-8").strip()
    assert [task["story_only"] for task in tasks] == [False] * 10 + [True] * 5
    assert tasks[-1]["name"] == "story-only solver 5"
    assert tasks[-1]["has_accusation"] is True
    assert Path(tasks[-1]["packet_file"]).name == "stage-story-only.md"
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
    make_fake_pdfs(game_dir)
    exported = run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out")])
    assert exported["ok"] is True
    assert Path(exported["folder"]).name == "The Lens of Gull Rock"


def test_judge_reports_failing_items_with_their_files(game_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_plan(game_dir)
    packets = run(["packets", "--game", str(game_dir)])
    tasks = packets["solver_tasks"]
    codes = {"A": ("A1", "A2"), "B": ("B1",), "story-only": ()}

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
    assert by_code["deduction"]["name"] == "deduction"
    # The plan's must_contain repeats the clue quotes, so the deduction fixer changes both together.
    assert by_code["deduction"]["files"] == [
        "story.yaml",
        "plan.yaml",
        "documents/D1.md",
        "documents/D5.md",
        "images/",
    ]
    assert "who" not in by_code
    assert "why" not in by_code
    assert by_code["deduction"]["verdict"] == "too_hard"
    deduction_notes = json.loads(Path(by_code["deduction"]["findings_file"]).read_text(encoding="utf-8"))
    assert [question["verdict"]["code"] for question in deduction_notes["questions"]] == ["who", "why"]
    notes = json.loads(Path(by_code["A1"]["findings_file"]).read_text(encoding="utf-8"))
    assert notes["verdict"]["verdict"] == "too_hard"
    assert len(notes["solver_answers"]) == 5
    status = run(["status", "--game", str(game_dir), "--panel", "false"])
    assert status["ok"] is False
    assert status["stale"]
    # The panel failed these codes on their current content: they are stale, but a new panel round would only repeat
    # the same verdicts, so none of them is unjudged.
    judged_status = run(["status", "--game", str(game_dir)])
    assert "A1" in judged_status["panel_stale"]
    assert judged_status["panel_unjudged"] == []


def test_packets_skip_the_stages_that_passed_on_their_current_content(game_dir: Path) -> None:
    write_plan(game_dir)
    assert run(["check", "--game", str(game_dir)])["ok"] is True
    assert run(["judge", "--game", str(game_dir), "--input", json.dumps(packets_and_payload(game_dir))])["ok"] is True
    again = run(["packets", "--game", str(game_dir)])
    assert again["solver_tasks"] == []
    assert again["skipped_stages"] == ["A", "B", "story-only"]
    path = game_dir / "source" / "documents" / "D4.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nThe gulls were loud that night.\n", encoding="utf-8")
    assert run(["check", "--game", str(game_dir)])["ok"] is True
    payload = packets_and_payload(game_dir)
    # The panel judged these stages before, so the re-test of the fix gets 3 solvers, not the 5 of the first round.
    assert [task["stage"] for task in payload["solver_tasks"]] == ["B"] * 3 + ["story-only"] * 3
    judged = run(["judge", "--game", str(game_dir), "--input", json.dumps(payload)])
    assert judged["ok"] is True
    report = json.loads((game_dir / "reports" / "panel" / "panel.json").read_text(encoding="utf-8"))
    assert [item["code"] for item in report["puzzles"]] == ["B1"]
    assert run(["status", "--game", str(game_dir)])["ok"] is True
    assert len(run(["packets", "--game", str(game_dir), "--all"])["solver_tasks"]) == 3 * 5


def test_judge_sends_a_story_only_proof_to_the_deduction_fixer(game_dir: Path) -> None:
    write_plan(game_dir)
    payload = packets_and_payload(game_dir)
    for task, result in zip(payload["solver_tasks"], payload["solver_results"], strict=True):
        if task["story_only"]:
            result["accusation"] = accusation("B")[1:]
    judged = run(["judge", "--game", str(game_dir), "--input", json.dumps(payload)])
    assert judged["ok"] is False
    assert judged["failing"] == ["why: puzzles not needed: 5 of 5 solvers proved it without any puzzle answer"]
    (deduction,) = judged["failing_items"]
    assert (deduction["code"], deduction["verdict"]) == ("deduction", "puzzles_not_needed")
    notes = json.loads(Path(deduction["findings_file"]).read_text(encoding="utf-8"))
    assert notes["questions"] == []
    (why,) = notes["puzzles_not_needed"]
    assert why["verdict"]["code"] == "why"
    assert [choice["solver"] for choice in why["solver_choices"]] == [f"story-only solver {n}" for n in range(1, 6)]
    assert why["solver_answers"] == []


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
    result = run(["export", "--game", str(game_dir), "--force"])
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
    payload = '{"solver_tasks": [], "solver_results": []}'
    result = run(["judge", "--game", str(game_dir), "--input", payload])
    assert result["ok"] is False
    assert result["errors"] >= 1


def test_render_without_a_companion_page(game_dir: Path) -> None:
    run(["render", "--game", str(game_dir), "--html-only"])
    assert (game_dir / "render" / "Game companion.html").is_file()
    set_config(game_dir, assistance__companion_page=False)
    result = run(["render", "--game", str(game_dir), "--html-only"])
    assert result["ok"] is True
    assert not (game_dir / "render" / "Game companion.html").exists()


def test_render_and_export_name_the_files_in_the_game_language(game_dir: Path, tmp_path: Path) -> None:
    set_config(game_dir, language="es")
    assert run(["render", "--game", str(game_dir), "--html-only"])["ok"] is True
    assert (game_dir / "render" / "Compañero de juego.html").is_file()
    assert not (game_dir / "render" / "Game companion.html").exists()
    make_fake_pdfs(game_dir, output_file_names("es"))
    exported = run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out"), "--force"])
    assert exported["ok"] is True
    assert exported["files"] == [
        "0 - LEE ESTO PRIMERO (avisos).txt",
        "1 - EMPIEZA AQUÍ (manual).pdf",
        "2 - IMPRIME ESTO (materiales del juego).pdf",
        "Compañero de juego.html",
        "SOLO ANFITRIÓN - spoilers/3 - Pistas.pdf",
        "SOLO ANFITRIÓN - spoilers/4 - Soluciones.pdf",
    ]


def test_full_check_records_a_pass_for_every_code_in_the_ledger(game_dir: Path) -> None:
    assert run(["check", "--game", str(game_dir)])["ok"] is True
    ledger = json.loads((game_dir / "reports" / "verification.json").read_text(encoding="utf-8"))
    entries: dict[str, Any] = ledger["entries"]
    assert sorted(entries) == ["A1", "A2", "B1", "deduction"]
    for entry in entries.values():
        assert entry["checks_hash"] is not None
        assert entry["checks_pass_hash"] == entry["checks_hash"]
        assert entry["panel_pass_hash"] is None


def test_a_full_check_with_errors_records_nothing_in_the_ledger(game_dir: Path) -> None:
    path = game_dir / "source" / "puzzles" / "P1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("my code goes back three steps", "no such words"), "utf-8")
    assert run(["check", "--game", str(game_dir)])["ok"] is False
    assert not (game_dir / "reports" / "verification.json").exists()


def test_broken_front_matter_and_plan_entries_are_findings_not_crashes(game_dir: Path) -> None:
    (game_dir / "source" / "documents" / "D6.md").write_text("---\nid: D6\nkind: [letter\n---\nText\n", "utf-8")
    plan = "format_version: 1\npuzzles:\n  - stage: A\nstory_documents:\n"
    (game_dir / "source" / "plan.yaml").write_text(plan, encoding="utf-8")
    for scope in ("story", "plan", "full"):
        result = run(["check", "--game", str(game_dir), "--scope", scope])
        assert result["ok"] is (scope == "story"), result
    full = run(["check", "--game", str(game_dir)])
    assert "yaml.syntax" in [finding["rule"] for finding in full["findings"]]


def test_an_empty_plan_puzzle_list_is_a_finding(game_dir: Path) -> None:
    (game_dir / "source" / "plan.yaml").write_text("format_version: 1\npuzzles:\n", encoding="utf-8")
    result = run(["check", "--game", str(game_dir), "--scope", "plan"])
    assert result["ok"] is False
    assert result["errors"] >= 1


def move_puzzle_to_stage(game_dir: Path, stage: str) -> None:
    path = game_dir / "source" / "puzzles" / "P2.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("stage: A", f"stage: {stage}"), "utf-8")


def test_a_puzzle_in_a_stage_that_the_flow_lacks_is_a_finding(game_dir: Path) -> None:
    move_puzzle_to_stage(game_dir, "Z")
    result = run(["check", "--game", str(game_dir)])
    assert result["ok"] is False
    assert result["errors"] >= 1
    assert not (game_dir / "reports" / "verification.json").exists()
    assert "ok" in run(["packets", "--game", str(game_dir)])


def test_a_crash_inside_a_verb_prints_one_json_line_and_exits_2(
    game_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(game_dir: Path) -> list[Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr("mystery_forge.cli_game.check_story_folder", explode)
    output = io.StringIO()
    assert cli.main(["check", "--game", str(game_dir), "--scope", "story"], output) == 2
    assert json.loads(output.getvalue()) == {"ok": False, "message": "RuntimeError: boom"}


def packets_and_payload(game_dir: Path) -> dict[str, Any]:
    tasks = run(["packets", "--game", str(game_dir)])["solver_tasks"]
    results = [
        {"status": "done", "answers": solver_answers(task["stage"]), "accusation": accusation(task["stage"])}
        for task in tasks
    ]
    return {"solver_tasks": tasks, "solver_results": results, "guesser_result": {"guesses": []}}


@pytest.mark.parametrize(
    "stdin",
    [
        "not json",
        "[1, 2]",
        json.dumps({"solver_tasks": 3}),
        json.dumps({"solver_tasks": [{"name": "A solver 1", "stage": "A"}], "solver_results": []}),
        json.dumps({"solver_tasks": [{"name": "x", "stage": "A"}], "solver_results": [{"answers": [{"x": 1}]}]}),
    ],
)
def test_judge_reports_bad_input_as_a_finding(game_dir: Path, monkeypatch: pytest.MonkeyPatch, stdin: str) -> None:
    judged = run(["judge", "--game", str(game_dir)], stdin, monkeypatch)
    assert judged["ok"] is False
    assert judged["findings"][0]["rule"] == "judge.input"
    assert judged["failing_items"] == []


def test_judge_without_packets_asks_for_them(game_dir: Path) -> None:
    payload: dict[str, Any] = {"solver_tasks": [], "solver_results": [], "guesser_result": None}
    judged = run(["judge", "--game", str(game_dir), "--input", json.dumps(payload)])
    assert judged["ok"] is False
    assert "run forge packets first" in judged["message"]
    panel = game_dir / "reports" / "panel"
    panel.mkdir(parents=True)
    for broken in ("{not json", '{"stage": "A"}', "7"):
        (panel / "packets.json").write_text(broken, encoding="utf-8")
        judged = run(["judge", "--game", str(game_dir), "--input", json.dumps(payload)])
        assert "run forge packets first" in judged["message"]


def test_judge_refuses_stale_packets(game_dir: Path) -> None:
    payload = packets_and_payload(game_dir)
    path = game_dir / "source" / "documents" / "D3.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8")
    judged = run(["judge", "--game", str(game_dir), "--input", json.dumps(payload)])
    assert judged["ok"] is False
    assert "packets are stale, run the panel again" in judged["message"]
    assert not (game_dir / "reports" / "panel" / "panel.json").exists()


def test_render_without_a_browser_reports_the_doctor_fix(game_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from mystery_forge.render.pdf import BrowserNotFoundError

    def no_browser() -> Any:
        raise BrowserNotFoundError("No browser.")

    monkeypatch.setattr("mystery_forge.cli_game.open_sheet_browser", no_browser)
    result = run(["render", "--game", str(game_dir)])
    assert result["ok"] is False
    assert "No browser." in result["message"]
    assert "playwright install chromium" in result["fix"]
    assert result["fix_groups"] == []


def test_render_reports_a_browser_error_during_the_render(game_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from playwright.sync_api import Error as PlaywrightError

    def failing_render(*arguments: Any) -> Any:
        raise PlaywrightError("Target closed")

    monkeypatch.setattr("mystery_forge.cli_game.open_sheet_browser", lambda: contextlib.nullcontext(None))
    monkeypatch.setattr("mystery_forge.cli_game.render_game", failing_render)
    result = run(["render", "--game", str(game_dir)])
    assert result["ok"] is False
    assert "Target closed" in result["message"]


def test_export_refuses_a_game_that_verification_blocks(game_dir: Path, tmp_path: Path) -> None:
    make_fake_pdfs(game_dir)
    assert run(["check", "--game", str(game_dir)])["ok"] is True
    blocked = run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out")])
    assert blocked["ok"] is False
    assert {finding["rule"] for finding in blocked["findings"]} == {"verification.stale"}
    assert not (tmp_path / "out").exists()
    without_panel = run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out"), "--panel", "False"])
    assert without_panel["ok"] is True
    assert without_panel["warnings"] == []
    assert without_panel["files"][0] == "1 - START HERE (manual).pdf"
    path = game_dir / "source" / "documents" / "D3.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8")
    assert run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out"), "--panel", "false"])["ok"] is False
    forced = run(["export", "--game", str(game_dir), "--to", str(tmp_path / "out"), "--force"])
    assert forced["ok"] is True
    # The host sees the problems in a file of the game folder, and the agent gets them in plain words for its report.
    assert forced["files"][0] == "0 - READ FIRST (warnings).txt"
    assert forced["warnings"][-1] == (
        "Accusation form: the automatic checks did not run after the last change. The test players did not try it "
        "after the last change."
    )


def make_fake_pdfs(game_dir: Path, names: OutputFileNames | None = None) -> None:
    (game_dir / "render").mkdir(exist_ok=True)
    for name in (names or output_file_names("en")).pdfs.values():
        (game_dir / "render" / name).write_bytes(b"%PDF")


def test_status_lists_stale_checks_and_stale_panel_codes_apart(game_dir: Path) -> None:
    status = run(["status", "--game", str(game_dir)])
    assert status["checks_stale"] == ["A1", "A2", "B1", "deduction"]
    assert status["panel_stale"] == ["A1", "A2", "B1", "deduction"]
    run(["check", "--game", str(game_dir)])
    status = run(["status", "--game", str(game_dir), "--panel", "True"])
    assert status["checks_stale"] == []
    assert status["panel_stale"] == ["A1", "A2", "B1", "deduction"]
    assert status["panel_unjudged"] == ["A1", "A2", "B1", "deduction"]
    status = run(["status", "--game", str(game_dir), "--panel", "0"])
    assert status["ok"] is True
    assert status["panel_stale"] == status["panel_unjudged"] == []


def break_story_and_puzzle(game_dir: Path) -> None:
    move_puzzle_to_stage(game_dir, "Z")
    path = game_dir / "source" / "puzzles" / "P1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("my code goes back three steps", "no such words"), "utf-8")


def test_check_only_reports_the_listed_files_and_no_write_writes_nothing(game_dir: Path) -> None:
    break_story_and_puzzle(game_dir)
    everything = run(["check", "--game", str(game_dir), "--no-write"])
    assert len({finding.get("file") for finding in everything["findings"]}) > 1
    assert not (game_dir / "reports").exists()
    assert not (game_dir / "game.json").exists()
    assert everything["report"] is None
    assert all("findings_file" not in group for group in everything["fix_groups"])
    only = run(["check", "--game", str(game_dir), "--only", "puzzles/P1.yaml,documents/D2.md", "--no-write"])
    assert {finding.get("file") for finding in only["findings"]} <= {"puzzles/P1.yaml", "documents/D2.md"}
    assert only["findings"]
    assert [group["name"] for group in only["fix_groups"]] == ["P1"]
    assert not (game_dir / "reports").exists()


def test_assemble_and_render_accept_only_and_no_write(game_dir: Path) -> None:
    assembled = run(["assemble", "--game", str(game_dir), "--no-write", "--only", "story.yaml"])
    assert assembled["ok"] is True
    assert assembled["report"] is None
    assert not (game_dir / "game.json").exists()
    rendered = run(["render", "--game", str(game_dir), "--html-only", "--no-write"])
    assert rendered["ok"] is True
    assert rendered["previews_dir"] is None
    assert not (game_dir / "render").exists()
    assert not (game_dir / "reports").exists()
    path = game_dir / "source" / "puzzles" / "P2.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("difficulty: easy", "difficulty: trivial"), "utf-8")
    broken = run(["render", "--game", str(game_dir), "--html-only", "--no-write", "--only", "story.yaml"])
    assert broken["ok"] is False
    assert broken["findings"] == []
    assert not (game_dir / "reports").exists()


@pytest.mark.parametrize(
    "verb", ["assemble", "check", "writer-tasks", "packets", "judge", "status", "render", "export"]
)
def test_a_game_verb_refuses_a_folder_without_source_and_writes_nothing(tmp_path: Path, verb: str) -> None:
    mistyped = tmp_path / "games2026-10-07-game-3"
    output = io.StringIO()
    assert cli.main([verb, "--game", str(mistyped)], output) == 2
    result = json.loads(output.getvalue())
    assert result["ok"] is False
    assert "has no source folder" in result["message"]
    assert not mistyped.exists()


def test_strings_writes_the_template_for_a_language_without_a_checked_table(
    game_dir: Path, restored_tables: None
) -> None:
    assert run(["strings", "--game", str(game_dir)]) == {"ok": True, "needed": False}
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["language"] = "ja"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    first = run(["strings", "--game", str(game_dir)])
    assert (first["ok"], first["needed"], first["language"]) == (False, True, "ja")
    assert first["findings"][0]["rule"] == "strings.missing"
    template = Path(first["template"])
    assert json.loads(template.read_text(encoding="utf-8"))["strings"]["envelope_label"] == "Envelope {stage}"
    Path(first["target"]).write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    second = run(["strings", "--game", str(game_dir)])
    assert (second["ok"], second["needed"]) == (True, True)
    config_path.unlink()
    assert run(["strings", "--game", str(game_dir)])["ok"] is False


def test_material_shows_what_the_page_of_one_puzzle_prints(game_dir: Path) -> None:
    shown = run(["material", "--game", str(game_dir), "--puzzle", "P1"])
    assert shown["ok"] is True
    assert shown["code"] == "A1"
    # The caesar builder prints the plaintext shifted by 3.
    assert "NHBV LQ WKH ERDWKRXVH" in shown["material"]
    assert shown["print_notes"] == []
    missing = run(["material", "--game", str(game_dir), "--puzzle", "P9"])
    assert missing["ok"] is False
    assert "P1, P2, P3" in missing["message"]
    path = game_dir / "source" / "puzzles" / "P1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("shift: 3", "shift: 99"), encoding="utf-8")
    broken = run(["material", "--game", str(game_dir), "--puzzle", "P1"])
    assert broken["ok"] is False
    assert broken["findings"][0]["rule"] == "mechanic.params"
    (game_dir / "source" / "story.yaml").unlink()
    assert run(["material", "--game", str(game_dir), "--puzzle", "P1"])["ok"] is False


def plain_answer(option: str, quote: str) -> dict[str, Any]:
    evidence = [{"document": "D4", "quote": quote}]
    return {
        "status": "done",
        "answers": [],
        "accusation": [{"question": "who", "option": option, "evidence": evidence}],
    }


def test_plain_test_writes_the_packet_and_judges_the_answers(game_dir: Path) -> None:
    written = run(["plain-test", "--game", str(game_dir)])
    assert written["ok"] is True
    tasks = written["solver_tasks"]
    assert [task["name"] for task in tasks] == ["plain clues 1", "plain clues 2", "plain clues 3"]
    assert "wet boot prints" in Path(tasks[0]["packet_file"]).read_text(encoding="utf-8")
    proof = plain_answer("felix", "wet boot prints on the lamp room stairs, too big for Ana")
    judge_input = json.dumps({"solver_tasks": tasks, "solver_results": [proof, proof, proof]})
    judged = run(["plain-test", "--game", str(game_dir), "--judge", "--input", judge_input])
    assert judged["ok"] is False
    assert judged["failing"] == ["who: the plain clues prove the answer without a puzzle"]
    assert judged["failing_questions"] == [
        {"question": "who", "quotes": ["wet boot prints on the lamp room stairs, too big for Ana"]}
    ]
    assert Path(judged["report"]).is_file()
    stuck = plain_answer("", "")
    clean_input = json.dumps({"solver_tasks": tasks, "solver_results": [stuck, stuck, stuck]})
    assert run(["plain-test", "--game", str(game_dir), "--judge", "--input", clean_input])["ok"] is True
    broken = run(["plain-test", "--game", str(game_dir), "--judge", "--input", "{}"])
    assert broken["ok"] is False and broken["failing"]


def test_plain_test_without_an_accusation_or_a_story(game_dir: Path) -> None:
    story_path = game_dir / "source" / "story.yaml"
    story = yaml.safe_load(story_path.read_text(encoding="utf-8"))
    del story["deduction"]
    story_path.write_text(yaml.safe_dump(story, allow_unicode=True), encoding="utf-8")
    assert run(["plain-test", "--game", str(game_dir)]) == {"ok": True, "solver_tasks": [], "failing": []}
    story_path.unlink()
    missing = run(["plain-test", "--game", str(game_dir)])
    assert missing["ok"] is False and missing["findings"]
