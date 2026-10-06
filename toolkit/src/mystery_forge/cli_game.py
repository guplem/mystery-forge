"""The `forge` verbs that work on one game folder: check, writer-tasks, packets, judge, status, render, export.

`cli.py` holds the parser and the verbs that need no game. Each function here takes the parsed arguments and the
output stream, prints one JSON object, and returns the exit code.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final, TextIO

from mystery_forge.assemble import AssemblyResult, assemble_game
from mystery_forge.checks.runner import run_checks
from mystery_forge.cli_output import capped_findings, emit, write_report
from mystery_forge.export import ExportError, export_game, output_root
from mystery_forge.findings import Finding, count_errors, findings_to_json
from mystery_forge.fix_groups import (
    DOCUMENTS_GROUP,
    file_owners,
    group_files,
    group_findings,
    write_fix_groups,
)
from mystery_forge.game import Game
from mystery_forge.mechanics.registry import all_implementations
from mystery_forge.panel.judge import judge_panel, report_summary
from mystery_forge.panel.models import GuesserResult, ItemVerdict, PanelReport, SolverResult
from mystery_forge.panel.packets import StagePacket, build_guesser_packet, build_stage_packets
from mystery_forge.paths import SystemFolders
from mystery_forge.plan import PLAN_FILE, Plan, check_plan_folder
from mystery_forge.render.companion_data import build_companion_html
from mystery_forge.render.game_renderer import RenderReport, render_game
from mystery_forge.render.manual import COMPANION_FILE
from mystery_forge.render.pdf import open_sheet_browser
from mystery_forge.render_checks import check_rendered
from mystery_forge.spec.loader import SOURCE_FOLDER, load_required_model
from mystery_forge.story_checks import check_story_folder
from mystery_forge.verification import (
    export_blockers,
    game_hashes,
    ledger_path,
    load_ledger,
    record_checks,
    record_panel,
    save_ledger,
    stale_codes,
)

RENDER_FOLDER: Final[str] = "render"
PANEL_FOLDER: Final[str] = "panel"
PREVIEW_FOLDER: Final[str] = "previews"
SOLVER_PERSONAS: Final[tuple[str, ...]] = (
    "Read every document slowly and literally. Trust only what is written.",
    "Think laterally. Look for hidden patterns, odd details, and wordplay.",
    "Work fast: test your first idea against the evidence, then move on.",
    "Be a skeptic: before you answer, try hard to find a second answer that also fits.",
    "Play like a careful newcomer to puzzle games who reads every instruction twice.",
)
KIDS_PERSONA: Final[str] = "Play like a bright 10-year-old: you know the alphabet and simple sums, not trivia."


def assemble_or_report(game_dir: Path, output: TextIO, label: str) -> Game | None:
    """Assemble the game. Print an `ok: false` result with fix groups when it has errors."""
    result: AssemblyResult = assemble_game(game_dir)
    if result.game is not None and count_errors(result.findings) == 0:
        return result.game
    groups = write_fix_groups(group_findings(result.findings, game_dir), game_dir, label)
    report: Path = write_report(game_dir, label, {"findings": findings_to_json(result.findings)})
    emit(output, {"ok": False, "report": str(report), "fix_groups": groups, **capped_findings(result.findings)})
    return None


def command_check(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    scope: str = arguments.scope
    findings: list[Finding]
    if scope == "story":
        findings = check_story_folder(game_dir)
    elif scope == "plan":
        findings = check_plan_folder(game_dir, frozenset(all_implementations()))
    else:
        findings = full_check(game_dir)
    groups = write_fix_groups(group_findings(findings, game_dir), game_dir, scope)
    report: Path = write_report(game_dir, f"check-{scope}", {"findings": findings_to_json(findings)})
    emit(
        output,
        {
            "ok": count_errors(findings) == 0,
            "scope": scope,
            "report": str(report),
            "fix_groups": groups,
            **capped_findings(findings),
        },
    )
    return 0


def full_check(game_dir: Path) -> list[Finding]:
    """Assemble and run every game check. Record the result in the verification ledger."""
    result: AssemblyResult = assemble_game(game_dir)
    findings: list[Finding] = list(result.findings)
    if result.game is None:
        return findings
    (game_dir / "game.json").write_text(result.game.model_dump_json(indent=2), encoding="utf-8")
    findings.extend(run_checks(result.game))
    hashes: dict[str, str] = game_hashes(result.game)
    passing: list[str] = list(hashes) if count_errors(findings) == 0 else []
    path: Path = ledger_path(game_dir)
    save_ledger(path, record_checks(load_ledger(path), hashes, passing))
    return findings


def command_writer_tasks(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    findings: list[Finding] = []
    plan: Plan | None = load_required_model(game_dir / SOURCE_FOLDER, PLAN_FILE, Plan, findings)
    if plan is None:
        emit(output, {"ok": False, "tasks": [], **capped_findings(findings)})
        return 0
    tasks: list[dict[str, Any]] = [
        {
            "name": f"{puzzle.id} {puzzle.mechanic}",
            "id": puzzle.id,
            "stage": puzzle.stage,
            "mechanic": puzzle.mechanic,
            "documents": puzzle.documents,
            "relies_on": puzzle.relies_on,
        }
        for puzzle in plan.puzzles
    ]
    emit(output, {"ok": True, "tasks": tasks})
    return 0


def command_packets(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    game: Game | None = assemble_or_report(game_dir, output, "packets")
    if game is None:
        return 0
    folder: Path = game_dir / "reports" / PANEL_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    packets: list[StagePacket] = build_stage_packets(game)
    (folder / "packets.json").write_text(
        json.dumps([packet.model_dump() for packet in packets], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    personas: list[str] = list(SOLVER_PERSONAS)
    if game.config.audience == "kids":
        personas[-1] = KIDS_PERSONA
    tasks: list[dict[str, Any]] = []
    for packet in packets:
        packet_file: Path = folder / f"stage-{packet.stage}.md"
        packet_file.write_text(packet.text, encoding="utf-8")
        for number in range(1, game.brief.solver_count + 1):
            tasks.append(
                {
                    "name": f"{packet.stage} solver {number}",
                    "stage": packet.stage,
                    "solver": number,
                    "persona": personas[(number - 1) % len(personas)],
                    "packet_file": str(packet_file),
                    "has_accusation": bool(packet.questions),
                }
            )
    guesser_file: Path = folder / "guesser.md"
    guesser_file.write_text(build_guesser_packet(game).text, encoding="utf-8")
    emit(output, {"ok": True, "solver_tasks": tasks, "guesser_file": str(guesser_file)})
    return 0


def command_judge(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    payload: dict[str, Any] = json.loads(sys.stdin.read() if arguments.input is None else arguments.input)
    game: Game | None = assemble_or_report(game_dir, output, "judge")
    if game is None:
        return 0
    folder: Path = game_dir / "reports" / PANEL_FOLDER
    packets: list[StagePacket] = [
        StagePacket.model_validate(item) for item in json.loads((folder / "packets.json").read_text(encoding="utf-8"))
    ]
    results: list[SolverResult] = [
        solver_result(task, result)
        for task, result in zip(payload["solver_tasks"], payload["solver_results"], strict=True)
    ]
    guesser: GuesserResult | None = (
        GuesserResult.model_validate(payload["guesser_result"]) if payload.get("guesser_result") else None
    )
    report: PanelReport = judge_panel(game, packets, results, guesser)
    report_file: Path = folder / "panel.json"
    report_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    path: Path = ledger_path(game_dir)
    save_ledger(path, record_panel(load_ledger(path), game_hashes(game), report))
    summary: dict[str, Any] = report_summary(report)
    failing_items: list[dict[str, Any]] = failing_panel_items(game, game_dir, report, results)
    emit(
        output,
        {
            "ok": report.ok,
            "verdicts": summary["verdicts"],
            "invalid_solvers": summary["invalid_solvers"],
            "failing": [f"{item['code']}: {item['reason']}" for item in summary["failing"]],
            "failing_items": failing_items,
            "report": str(report_file),
        },
    )
    return 0


def solver_result(task: dict[str, Any], result: dict[str, Any]) -> SolverResult:
    return SolverResult(
        solver=str(task["name"]),
        stage=str(task["stage"]),
        answers=result.get("answers", []),
        accusation=result.get("accusation", []),
        status=result.get("status", "done"),
    )


def failing_panel_items(
    game: Game, game_dir: Path, report: PanelReport, results: list[SolverResult]
) -> list[dict[str, Any]]:
    """One fix task per failing puzzle or question, with its own findings file of solver notes."""
    owners: dict[str, str] = file_owners(game_dir)
    puzzle_ids: dict[str, str] = {puzzle.code: puzzle.source.id for puzzle in game.puzzles}
    items: list[dict[str, Any]] = []
    for verdict in [*report.puzzles, *report.questions]:
        if verdict.verdict == "pass":
            continue
        puzzle_id: str | None = puzzle_ids.get(verdict.code)
        files: list[str] = (
            group_files(puzzle_id, owners)
            if puzzle_id is not None
            else ["story.yaml", *group_files(DOCUMENTS_GROUP, owners)]
        )
        findings_file: Path = game_dir / "reports" / f"fix-panel-{verdict.code}.json"
        findings_file.write_text(
            json.dumps(panel_item_notes(verdict, results), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        items.append(
            {
                "name": f"{verdict.code} {verdict.verdict}",
                "code": verdict.code,
                "verdict": verdict.verdict,
                "files": files,
                "findings_file": str(findings_file),
            }
        )
    return items


def panel_item_notes(verdict: ItemVerdict, results: list[SolverResult]) -> dict[str, Any]:
    answers: list[dict[str, Any]] = [
        {"solver": result.solver, **answer.model_dump()}
        for result in results
        for answer in result.answers
        if answer.code == verdict.code
    ]
    choices: list[dict[str, Any]] = [
        {"solver": result.solver, **choice.model_dump()}
        for result in results
        for choice in result.accusation
        if choice.question == verdict.code
    ]
    return {"verdict": verdict.model_dump(), "solver_answers": answers, "solver_choices": choices}


def command_status(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    game: Game | None = assemble_or_report(game_dir, output, "status")
    if game is None:
        return 0
    panel_required: bool = arguments.panel.lower() in ("true", "1", "yes")
    hashes: dict[str, str] = game_hashes(game)
    ledger = load_ledger(ledger_path(game_dir))
    blockers: list[Finding] = export_blockers(ledger, hashes, panel_required)
    emit(
        output,
        {"ok": not blockers, "stale": stale_codes(ledger, hashes, panel_required), **capped_findings(blockers)},
    )
    return 0


def command_render(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    game: Game | None = assemble_or_report(game_dir, output, "render")
    if game is None:
        return 0
    render_dir: Path = game_dir / RENDER_FOLDER
    if arguments.html_only:
        report: RenderReport = render_game(game, render_dir, None)
    else:
        with open_sheet_browser() as browser:
            report = render_game(game, render_dir, browser)
    if game.config.assistance.companion_page:
        (render_dir / COMPANION_FILE).write_text(build_companion_html(game), encoding="utf-8")
    # Without a browser nothing was read back from the pages, so only the HTML was written and nothing can be checked.
    rendered_findings: list[Finding] = (
        [] if arguments.html_only else check_rendered(game, report, all_implementations())
    )
    findings: list[Finding] = [*report.findings, *rendered_findings]
    groups = write_fix_groups(group_findings(findings, game_dir), game_dir, "render")
    report_file: Path = write_report(game_dir, "render", {"findings": findings_to_json(findings)})
    emit(
        output,
        {
            "ok": count_errors(findings) == 0,
            "theme": report.theme,
            "sheets": {output_id: rendered.sheet_count for output_id, rendered in report.outputs.items()},
            "previews_dir": str(render_dir / PREVIEW_FOLDER),
            "report": str(report_file),
            "fix_groups": groups,
            **capped_findings(findings),
        },
    )
    return 0


def command_export(arguments: argparse.Namespace, output: TextIO, folders: SystemFolders) -> int:
    game_dir: Path = Path(arguments.game)
    game: Game | None = assemble_or_report(game_dir, output, "export")
    if game is None:
        return 0
    root: Path = Path(arguments.to) if arguments.to else output_root(game.config.output.folder, folders.desktop)
    try:
        result = export_game(game_dir / RENDER_FOLDER, root, game.story.title)
    except ExportError as error:
        emit(output, {"ok": False, "message": str(error)})
        return 0
    emit(output, {"ok": True, "folder": str(result.folder), "files": result.files})
    return 0
