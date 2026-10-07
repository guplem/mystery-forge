"""The `forge` verbs that work on one game folder: check, writer-tasks, packets, judge, status, render, export.

`cli.py` holds the parser and the verbs that need no game. Each function here takes the parsed arguments and the
output stream, prints one JSON object, and returns the exit code.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Final, Self, TextIO

from playwright.sync_api import Error as PlaywrightError
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from mystery_forge.assemble import AssemblyResult, assemble_game
from mystery_forge.checks.runner import run_checks
from mystery_forge.cli_output import (
    BROWSER_FIX,
    OutputOptions,
    capped_findings,
    emit,
    input_problem,
    optional_report,
)
from mystery_forge.export import ExportError, ExportResult, export_game, output_root
from mystery_forge.findings import Finding, count_errors
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
from mystery_forge.panel.models import (
    AccusationChoice,
    GuesserResult,
    ItemVerdict,
    PanelReport,
    SolverAnswer,
    SolverResult,
    SolverStatus,
)
from mystery_forge.panel.packets import StagePacket, build_guesser_packet, build_stage_packets
from mystery_forge.paths import SystemFolders
from mystery_forge.plan import PLAN_FILE, Plan, check_plan_folder
from mystery_forge.render.companion_data import build_companion_html
from mystery_forge.render.game_renderer import PREVIEW_FOLDER, RenderReport, render_game
from mystery_forge.render.manual import COMPANION_FILE
from mystery_forge.render.pdf import BrowserNotFoundError, open_sheet_browser
from mystery_forge.render_checks import check_rendered
from mystery_forge.spec.loader import SOURCE_FOLDER, load_required_model
from mystery_forge.story_checks import check_story_folder
from mystery_forge.verification import (
    DEDUCTION_KEY,
    VerificationLedger,
    export_blockers,
    game_hashes,
    ledger_path,
    load_ledger,
    record_checks,
    record_panel,
    save_ledger,
    stale_check_codes,
    stale_codes,
    stale_panel_codes,
)

RENDER_FOLDER: Final[str] = "render"
PANEL_FOLDER: Final[str] = "panel"
PACKETS_FILE: Final[str] = "packets.json"
TRUE_WORDS: Final[frozenset[str]] = frozenset({"true", "1", "yes"})
SOLVER_PERSONAS: Final[tuple[str, ...]] = (
    "Read every document slowly and literally. Trust only what is written.",
    "Think laterally. Look for hidden patterns, odd details, and wordplay.",
    "Work fast: test your first idea against the evidence, then move on.",
    "Be a skeptic: before you answer, try hard to find a second answer that also fits.",
    "Play like a careful newcomer to puzzle games who reads every instruction twice.",
)
KIDS_PERSONA: Final[str] = "Play like a bright 10-year-old: you know the alphabet and simple sums, not trivia."


class SolverTask(BaseModel):
    """One solver task as `forge packets` printed it. The judge needs only its name and its stage."""

    model_config = ConfigDict(extra="ignore")

    name: str
    stage: str


class SolverOutput(BaseModel):
    """The output of one solver subagent. pskill may add its own fields next to these, so extra fields are ignored."""

    model_config = ConfigDict(extra="ignore")

    answers: list[SolverAnswer] = []
    accusation: list[AccusationChoice] = []
    status: SolverStatus = "done"


class JudgeInput(BaseModel):
    """The JSON that the judge reads on stdin: the tasks, one result per task in the same order, and the guess."""

    model_config = ConfigDict(extra="forbid")

    solver_tasks: list[SolverTask]
    solver_results: list[SolverOutput]
    guesser_result: GuesserResult | None = None

    @field_validator("guesser_result", mode="before")
    @classmethod
    def empty_guess_is_none(cls, value: object) -> object:
        return value if value else None

    @model_validator(mode="after")
    def one_result_per_task(self) -> Self:
        if len(self.solver_tasks) != len(self.solver_results):
            raise ValueError(f"{len(self.solver_tasks)} solver tasks but {len(self.solver_results)} solver results")
        return self


def output_options(arguments: argparse.Namespace) -> OutputOptions:
    return OutputOptions(only=arguments.only, write=not arguments.no_write)


def flag_is_true(text: str) -> bool:
    """Read a true/false flag. pskill prints Python booleans, so "True" and "False" count too."""
    return text.strip().lower() in TRUE_WORDS


def assemble_or_report(game_dir: Path, output: TextIO, label: str, options: OutputOptions | None = None) -> Game | None:
    """Assemble the game. Print an `ok: false` result with fix groups when it has errors."""
    chosen: OutputOptions = options if options is not None else OutputOptions()
    result: AssemblyResult = assemble_game(game_dir)
    if result.game is not None and count_errors(result.findings) == 0:
        return result.game
    findings: list[Finding] = chosen.selected(result.findings)
    groups: list[dict[str, Any]] = write_fix_groups(group_findings(findings, game_dir), game_dir, label, chosen.write)
    report: str | None = optional_report(game_dir, label, findings, chosen)
    emit(output, {"ok": False, "report": report, "fix_groups": groups, **capped_findings(findings)})
    return None


def command_check(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    scope: str = arguments.scope
    options: OutputOptions = output_options(arguments)
    all_findings: list[Finding]
    if scope == "story":
        all_findings = check_story_folder(game_dir)
    elif scope == "plan":
        all_findings = check_plan_folder(game_dir, frozenset(all_implementations()))
    else:
        all_findings = full_check(game_dir, options.write)
    findings: list[Finding] = options.selected(all_findings)
    groups: list[dict[str, Any]] = write_fix_groups(group_findings(findings, game_dir), game_dir, scope, options.write)
    report: str | None = optional_report(game_dir, f"check-{scope}", findings, options)
    emit(
        output,
        {
            "ok": count_errors(findings) == 0,
            "scope": scope,
            "report": report,
            "fix_groups": groups,
            **capped_findings(findings),
        },
    )
    return 0


def full_check(game_dir: Path, write: bool = True) -> list[Finding]:
    """Assemble and run every game check. Record a passing run in the verification ledger."""
    result: AssemblyResult = assemble_game(game_dir)
    findings: list[Finding] = list(result.findings)
    if result.game is None:
        return findings
    if write:
        (game_dir / "game.json").write_text(result.game.model_dump_json(indent=2), encoding="utf-8")
    findings.extend(run_checks(result.game))
    # A run with errors records nothing: the codes keep their last pass, which no longer matches, so they stay stale.
    if write and count_errors(findings) == 0:
        hashes: dict[str, str] = game_hashes(result.game)
        path: Path = ledger_path(game_dir)
        save_ledger(path, record_checks(load_ledger(path), hashes, hashes))
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
    (folder / PACKETS_FILE).write_text(
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


def emit_judge_problem(output: TextIO, finding: Finding) -> int:
    """Print a judge result that judged nothing, in the shape that the solver-panel skill reads."""
    emit(
        output,
        {
            "ok": False,
            "message": finding.message,
            "failing": [finding.message],
            "failing_items": [],
            "report": "",
            **capped_findings([finding]),
        },
    )
    return 0


def saved_packet_hashes(path: Path) -> list[str] | None:
    """Return the sha256 of each packet that `forge packets` wrote, or None when the file is missing or broken."""
    if not path.is_file():
        return None
    try:
        return [StagePacket.model_validate(item).sha256 for item in json.loads(path.read_text(encoding="utf-8"))]
    except (ValueError, TypeError):
        return None


def command_judge(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    raw_input: str = sys.stdin.read() if arguments.input is None else arguments.input
    try:
        judge_input: JudgeInput = JudgeInput.model_validate_json(raw_input)
    except ValidationError as error:
        first: str = str(error.errors()[0]["msg"])
        return emit_judge_problem(
            output,
            input_problem(
                "judge.input",
                f"The judge input is not valid: {first}.",
                "Pass {solver_tasks, solver_results, guesser_result} as JSON, with one result per task.",
            ),
        )
    game: Game | None = assemble_or_report(game_dir, output, "judge")
    if game is None:
        return 0
    folder: Path = game_dir / "reports" / PANEL_FOLDER
    saved_hashes: list[str] | None = saved_packet_hashes(folder / PACKETS_FILE)
    if saved_hashes is None:
        return emit_judge_problem(
            output,
            input_problem(
                "judge.no_packets",
                f"The panel folder has no readable {PACKETS_FILE}: run forge packets first.",
                "Run the solver panel from its first step.",
            ),
        )
    packets: list[StagePacket] = build_stage_packets(game)
    if [packet.sha256 for packet in packets] != saved_hashes:
        return emit_judge_problem(
            output,
            input_problem(
                "judge.stale_packets",
                "The game changed after the solvers got their packets: the packets are stale, run the panel again.",
                "Run the solver panel again on the current game.",
            ),
        )
    results: list[SolverResult] = [
        SolverResult(
            solver=task.name,
            stage=task.stage,
            answers=result.answers,
            accusation=result.accusation,
            status=result.status,
        )
        for task, result in zip(judge_input.solver_tasks, judge_input.solver_results, strict=True)
    ]
    report: PanelReport = judge_panel(game, packets, results, judge_input.guesser_result)
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


def failing_panel_items(
    game: Game, game_dir: Path, report: PanelReport, results: list[SolverResult]
) -> list[dict[str, Any]]:
    """One fix task per failing puzzle, plus one "deduction" task for all failing accusation questions.

    The questions share story.yaml, so one fixer takes them all: two fixers that edit one file in parallel lose
    each other's changes.
    """
    owners: dict[str, str] = file_owners(game_dir)
    puzzle_ids: dict[str, str] = {puzzle.code: puzzle.source.id for puzzle in game.puzzles}
    items: list[dict[str, Any]] = [
        panel_item(
            game_dir,
            verdict.code,
            f"{verdict.code} {verdict.verdict}",
            verdict,
            group_files(puzzle_ids[verdict.code], owners),
            panel_item_notes(verdict, results),
        )
        for verdict in report.puzzles
        if verdict.verdict != "pass"
    ]
    failing_questions: list[ItemVerdict] = [verdict for verdict in report.questions if verdict.verdict != "pass"]
    if failing_questions:
        items.append(
            panel_item(
                game_dir,
                DEDUCTION_KEY,
                DEDUCTION_KEY,
                failing_questions[0],
                ["story.yaml", *group_files(DOCUMENTS_GROUP, owners)],
                {"questions": [panel_item_notes(verdict, results) for verdict in failing_questions]},
            )
        )
    return items


def panel_item(
    game_dir: Path, code: str, name: str, verdict: ItemVerdict, files: list[str], notes: dict[str, Any]
) -> dict[str, Any]:
    """Write the solver notes of one fix task to its own findings file, and return the task item."""
    findings_file: Path = game_dir / "reports" / f"fix-panel-{code}.json"
    findings_file.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "name": name,
        "code": code,
        "verdict": verdict.verdict,
        "files": files,
        "findings_file": str(findings_file),
    }


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
    panel_required: bool = flag_is_true(arguments.panel)
    hashes: dict[str, str] = game_hashes(game)
    ledger: VerificationLedger = load_ledger(ledger_path(game_dir))
    blockers: list[Finding] = export_blockers(ledger, hashes, panel_required)
    emit(
        output,
        {
            "ok": not blockers,
            "stale": stale_codes(ledger, hashes, panel_required),
            "checks_stale": stale_check_codes(ledger, hashes),
            "panel_stale": stale_panel_codes(ledger, hashes) if panel_required else [],
            **capped_findings(blockers),
        },
    )
    return 0


def command_render(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    options: OutputOptions = output_options(arguments)
    game: Game | None = assemble_or_report(game_dir, output, "render", options)
    if game is None:
        return 0
    if options.write:
        return render_and_report(game, game_dir, game_dir / RENDER_FOLDER, arguments.html_only, options, output)
    # --no-write still renders, so the checks can read the pages, but into a folder that it deletes afterwards.
    scratch: Path = Path(tempfile.mkdtemp(prefix="forge-render-"))
    try:
        return render_and_report(game, game_dir, scratch, arguments.html_only, options, output)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def render_and_report(
    game: Game, game_dir: Path, render_dir: Path, html_only: bool, options: OutputOptions, output: TextIO
) -> int:
    report: RenderReport
    try:
        if html_only:
            report = render_game(game, render_dir, None)
        else:
            with open_sheet_browser() as browser:
                report = render_game(game, render_dir, browser)
    except (BrowserNotFoundError, PlaywrightError) as error:
        emit(output, {"ok": False, "message": str(error), "fix": BROWSER_FIX, "fix_groups": [], **capped_findings([])})
        return 0
    companion: Path = render_dir / COMPANION_FILE
    if game.config.assistance.companion_page:
        companion.write_text(build_companion_html(game), encoding="utf-8")
    else:
        # An earlier render may have written it; export copies whatever the folder holds.
        companion.unlink(missing_ok=True)
    # Without a browser nothing was read back from the pages, so only the HTML was written and nothing can be checked.
    rendered_findings: list[Finding] = [] if html_only else check_rendered(game, report, all_implementations())
    findings: list[Finding] = options.selected([*report.findings, *rendered_findings])
    groups: list[dict[str, Any]] = write_fix_groups(
        group_findings(findings, game_dir), game_dir, "render", options.write
    )
    emit(
        output,
        {
            "ok": count_errors(findings) == 0,
            "theme": report.theme,
            "sheets": {output_id: rendered.sheet_count for output_id, rendered in report.outputs.items()},
            "previews_dir": str(render_dir / PREVIEW_FOLDER) if options.write else None,
            "report": optional_report(game_dir, "render", findings, options),
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
    blockers: list[Finding] = export_blockers(
        load_ledger(ledger_path(game_dir)), game_hashes(game), flag_is_true(arguments.panel)
    )
    if blockers and not arguments.force:
        message: str = "The verification blocks the export: some checks or panel results are missing or failing."
        emit(output, {"ok": False, "message": message, **capped_findings(blockers)})
        return 0
    root: Path = Path(arguments.to) if arguments.to else output_root(game.config.output.folder, folders.desktop)
    try:
        result: ExportResult = export_game(game_dir / RENDER_FOLDER, root, game.story.title)
    except ExportError as error:
        emit(output, {"ok": False, "message": str(error)})
        return 0
    emit(output, {"ok": True, "folder": str(result.folder), "files": result.files, "blockers_ignored": len(blockers)})
    return 0
