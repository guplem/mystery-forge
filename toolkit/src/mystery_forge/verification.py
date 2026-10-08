"""Content hashes of what each check saw, and the ledger that tells export which results are still fresh.

A check result is valid only for the content that it checked (`adr/0004-verification-strategy.md`). A puzzle's
closure hash covers everything that a solver of its stage sees, plus the puzzle file itself. A fix to one document
therefore makes stale only the puzzles whose players hold that document, and export refuses those until they pass
again. The same ledger tells `forge packets` which stages the solver panel must run again.
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from mystery_forge.assemble import IMAGE_MARK_PATTERN
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledDocument, AssembledPuzzle, Game
from mystery_forge.panel.models import ItemVerdict, PanelReport, Verdict
from mystery_forge.panel.packets import STORY_ONLY_STAGE, available_documents, ordered_puzzles, stage_index
from mystery_forge.spec.models import Story

LEDGER_FILE: Final[Path] = Path("reports") / "verification.json"
DEDUCTION_KEY: Final[str] = "deduction"
LEDGER_FORMAT_VERSION: Final[int] = 1


class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # The hash at the last check run that covered this code, and at the last run that passed.
    checks_hash: str | None = None
    checks_pass_hash: str | None = None
    panel_hash: str | None = None
    panel_verdict: Verdict | None = None
    panel_pass_hash: str | None = None


class VerificationLedger(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: int = LEDGER_FORMAT_VERSION
    # By puzzle code, plus "deduction" for the accusation questions.
    entries: dict[str, LedgerEntry] = {}


def ledger_path(game_dir: Path) -> Path:
    return game_dir / LEDGER_FILE


def puzzle_closure_hash(game: Game, puzzle_id: str) -> str:
    puzzle: AssembledPuzzle = next(puzzle for puzzle in game.puzzles if puzzle.source.id == puzzle_id)
    stage: str = puzzle.source.stage
    documents: list[AssembledDocument] = available_documents(game, stage)
    opened_stages = game.flow.stages[: stage_index(game, stage) + 1]
    return content_hash(
        {
            "puzzle": puzzle.source.model_dump(mode="json"),
            "artifact": puzzle.artifact.model_dump(mode="json") if puzzle.artifact is not None else None,
            "documents": [document_content(document) for document in documents],
            "images": {image: game.images.get(image) for image in used_images(documents)},
            "registry": story_registry(game.story),
            # The rest of what the stage packet shows: the framing texts and the answers of earlier stages.
            "title": game.story.title,
            "intro": game.story.intro,
            "opening_texts": [opened.opening_text for opened in opened_stages],
            "answers_found": {
                earlier.code: earlier.source.answer
                for earlier in ordered_puzzles(game)
                if stage_index(game, earlier.source.stage) < stage_index(game, stage)
            },
        }
    )


def deduction_hash(game: Game) -> str:
    assert game.story.deduction is not None
    return content_hash(
        {
            "deduction": game.story.deduction.model_dump(mode="json"),
            "documents": [document_content(document) for document in game.documents],
            "registry": story_registry(game.story),
        }
    )


def game_hashes(game: Game) -> dict[str, str]:
    """Return the closure hash of every puzzle by its code, plus "deduction" when the story has one."""
    hashes: dict[str, str] = {
        puzzle.code: puzzle_closure_hash(game, puzzle.source.id) for puzzle in ordered_puzzles(game)
    }
    if game.story.deduction is not None:
        hashes[DEDUCTION_KEY] = deduction_hash(game)
    return hashes


def content_hash(content: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def document_content(document: AssembledDocument) -> dict[str, Any]:
    return {"meta": document.meta.model_dump(mode="json"), "text": document.text}


def used_images(documents: list[AssembledDocument]) -> list[str]:
    return sorted(
        {match.group(1) for document in documents for match in IMAGE_MARK_PATTERN.finditer(document.body_html)}
    )


def story_registry(story: Story) -> dict[str, Any]:
    return story.model_dump(mode="json", include={"characters", "locations", "objects", "timeline", "clues"})


def load_ledger(path: Path) -> VerificationLedger:
    """Return the ledger at `path`, or an empty one. An empty ledger makes every code stale, which is the safe side."""
    if not path.is_file():
        return VerificationLedger()
    try:
        return VerificationLedger.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, UnicodeDecodeError):
        return VerificationLedger()


def save_ledger(path: Path, ledger: VerificationLedger) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ledger.model_dump_json(indent=2) + "\n", encoding="utf-8")


def record_checks(
    ledger: VerificationLedger, hashes: dict[str, str], passing_codes: Iterable[str]
) -> VerificationLedger:
    """Return the ledger after a deterministic check run over every code in `hashes`."""
    passing: frozenset[str] = frozenset(passing_codes)
    entries: dict[str, LedgerEntry] = dict(ledger.entries)
    for code, current in hashes.items():
        entry: LedgerEntry = entries.get(code, LedgerEntry())
        entries[code] = entry.model_copy(
            update={
                "checks_hash": current,
                "checks_pass_hash": current if code in passing else entry.checks_pass_hash,
            }
        )
    return ledger.model_copy(update={"entries": entries})


def record_panel(ledger: VerificationLedger, hashes: dict[str, str], report: PanelReport) -> VerificationLedger:
    """Return the ledger after a panel run. The accusation questions and their story-only verdicts share one entry:
    "deduction"."""
    verdicts: dict[str, Verdict] = {item.code: item.verdict for item in report.puzzles}
    if report.questions:
        questions: list[ItemVerdict] = [*report.questions, *report.story_only]
        failing: list[Verdict] = [item.verdict for item in questions if item.verdict != "pass"]
        verdicts[DEDUCTION_KEY] = failing[0] if failing else "pass"
    entries: dict[str, LedgerEntry] = dict(ledger.entries)
    for code, verdict in verdicts.items():
        current: str | None = hashes.get(code)
        if current is None:
            continue
        entry: LedgerEntry = entries.get(code, LedgerEntry())
        entries[code] = entry.model_copy(
            update={
                "panel_hash": current,
                "panel_verdict": verdict,
                "panel_pass_hash": current if verdict == "pass" else entry.panel_pass_hash,
            }
        )
    return ledger.model_copy(update={"entries": entries})


def stale_codes(ledger: VerificationLedger, hashes: dict[str, str], panel_required: bool = True) -> list[str]:
    """Return the codes with no pass on their current content, in the checks or (when required) in the panel."""
    stale: list[str] = []
    for code, current in hashes.items():
        entry: LedgerEntry = ledger.entries.get(code, LedgerEntry())
        if entry.checks_pass_hash != current or (panel_required and entry.panel_pass_hash != current):
            stale.append(code)
    return stale


def stale_check_codes(ledger: VerificationLedger, hashes: dict[str, str]) -> list[str]:
    """Return the codes whose deterministic checks have no pass on their current content."""
    return [
        code for code, current in hashes.items() if ledger.entries.get(code, LedgerEntry()).checks_pass_hash != current
    ]


def stale_panel_codes(ledger: VerificationLedger, hashes: dict[str, str]) -> list[str]:
    """Return the codes whose solver panel has no pass on their current content."""
    return [
        code for code, current in hashes.items() if ledger.entries.get(code, LedgerEntry()).panel_pass_hash != current
    ]


def unjudged_panel_codes(ledger: VerificationLedger, hashes: dict[str, str]) -> list[str]:
    """Return the codes that the solver panel never judged on their current content.

    A code that failed the panel on its current content is stale but not unjudged: the same packet would get the same
    verdict, so a run gains nothing by sending it to the panel again before a fix changes it.
    """
    return [code for code, current in hashes.items() if ledger.entries.get(code, LedgerEntry()).panel_hash != current]


def panel_tested_stages(game: Game, ledger: VerificationLedger) -> set[str]:
    """Return the packet stages that the panel judged before, on any content: a re-test of them needs fewer solvers."""
    tested: set[str] = {code for code, entry in ledger.entries.items() if entry.panel_hash is not None}
    stages: set[str] = {puzzle.source.stage for puzzle in game.puzzles if puzzle.code in tested}
    if DEDUCTION_KEY in tested:
        stages.add(STORY_ONLY_STAGE)
    return stages


def panel_stages_to_run(game: Game, ledger: VerificationLedger) -> set[str]:
    """Return the packet stages that hold an item with no panel pass on its current content.

    A puzzle's hash covers everything that its stage packet shows, so a stage whose puzzles all passed on their
    current hashes would get the same packet again: running it costs solvers and proves nothing new. The accusation
    lives in the last stage packet and in the story-only packet.
    """
    stale: set[str] = set(stale_panel_codes(ledger, game_hashes(game)))
    stages: set[str] = {puzzle.source.stage for puzzle in game.puzzles if puzzle.code in stale}
    if DEDUCTION_KEY in stale:
        stages |= {game.flow.stages[-1].id, STORY_ONLY_STAGE}
    return stages


# What does not pass on the current content of a code: the checks fail or did not run, the panel did not run, or the
# panel's failing verdict.
ProblemKind = Literal["checks_failing", "checks_stale", "panel_stale"] | Verdict


@dataclass(frozen=True)
class ExportProblem:
    code: str
    kind: ProblemKind


def export_problems(ledger: VerificationLedger, hashes: dict[str, str], panel_required: bool) -> list[ExportProblem]:
    """Return one problem per code and per kind of result (checks, panel) that does not pass on the current content."""
    problems: list[ExportProblem] = []
    for code, current in hashes.items():
        entry: LedgerEntry = ledger.entries.get(code, LedgerEntry())
        if entry.checks_pass_hash != current:
            problems.append(ExportProblem(code, "checks_failing" if entry.checks_hash == current else "checks_stale"))
        if panel_required and entry.panel_pass_hash != current:
            verdict: Verdict | None = entry.panel_verdict if entry.panel_hash == current else None
            problems.append(ExportProblem(code, verdict if verdict is not None else "panel_stale"))
    return problems


def export_blockers(ledger: VerificationLedger, hashes: dict[str, str], panel_required: bool) -> list[Finding]:
    """Return one finding per export problem."""
    return [blocker_finding(problem) for problem in export_problems(ledger, hashes, panel_required)]


def blocker_finding(problem: ExportProblem) -> Finding:
    kind: ProblemKind = problem.kind
    if kind == "checks_failing" or kind == "checks_stale":
        return checks_blocker(problem.code, failing=kind == "checks_failing")
    if kind == "panel_stale":
        return panel_blocker(problem.code, None)
    return panel_blocker(problem.code, kind)


def checks_blocker(code: str, failing: bool) -> Finding:
    if failing:
        return Finding(
            severity="error",
            rule="verification.failing",
            message=f"The checks fail on {code}.",
            path=code,
            fix_hint="Fix the findings of the checks for this code, then run the checks again.",
        )
    return Finding(
        severity="error",
        rule="verification.stale",
        message=f"The checks did not run on the current content of {code}.",
        path=code,
        fix_hint="Run the checks again on the current game.",
    )


def panel_blocker(code: str, verdict: Verdict | None) -> Finding:
    if verdict is not None:
        return Finding(
            severity="error",
            rule="verification.failing",
            message=f"The solver panel gave {code} the verdict {verdict}.",
            path=code,
            fix_hint="Fix the puzzle with the panel report in reports/, then run the solver panel again.",
        )
    return Finding(
        severity="error",
        rule="verification.stale",
        message=f"The solver panel did not run on the current content of {code}.",
        path=code,
        fix_hint="Run the solver panel again for the stage of this code.",
    )
