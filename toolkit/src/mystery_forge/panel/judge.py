"""The judge: turn the solver panel's answers into one verdict per puzzle and per accusation question.

The rules come from `adr/0004-verification-strategy.md`. A solve counts only when every evidence quote is in the packet
that the solver got, so a solver that guesses right does not pass a puzzle. Same-model solvers make correlated
mistakes, so a wrong answer that two solvers share is a real signal of a second answer, not noise. A puzzle whose
material prints its own method is no puzzle: when half of the solvers that solved it say so, it is trivial.
"""

import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Final

from mystery_forge.answers import normalize_answer
from mystery_forge.checks.ledger import normalize_quote_text
from mystery_forge.game import Game
from mystery_forge.panel.models import (
    Alternative,
    AnswerCount,
    Candidate,
    Evidence,
    GuesserResult,
    InvalidSolver,
    ItemVerdict,
    PanelReport,
    SolverResult,
    Verdict,
)
from mystery_forge.panel.packets import StagePacket, canaries, ordered_puzzles
from mystery_forge.spec.models import AccusationQuestion, Difficulty

MIN_SOLVERS: Final[int] = 3
FULL_PANEL: Final[int] = 5
# Verified solves that a pass needs: (with 3 or 4 valid solvers, with 5 or more).
REQUIRED_SOLVES: Final[dict[Difficulty, tuple[int, int]]] = {
    "easy": (2, 3),
    "medium": (2, 3),
    "hard": (1, 2),
    "expert": (1, 2),
}
QUESTION_DIFFICULTY: Final[Difficulty] = "medium"
SHARED_WRONG_ANSWER: Final[int] = 2
GOLD_SUSPECT_AGREEMENT: Final[int] = 3
SUMMARY_LIMIT_BYTES: Final[int] = 4000
MAX_REASON_LENGTH: Final[int] = 100
MAX_ANSWER_LENGTH: Final[int] = 30


@dataclass(frozen=True)
class Attempt:
    """What one valid solver did with one puzzle or question."""

    solver: str
    raw: str
    # The comparable form of the answer; empty when the solver gave none.
    normalized: str
    correct: bool
    verified: bool
    stuck: bool
    reasoning: str
    # Each candidate with its comparable answer.
    candidates: tuple[tuple[str, Candidate], ...]
    all_steps_stated: bool = False
    aha: str = ""


@dataclass(frozen=True)
class ValidSolver:
    result: SolverResult
    packet: StagePacket
    comparable_packet: str


def judge_panel(
    game: Game,
    packets: list[StagePacket],
    solver_results: list[SolverResult],
    guesser_result: GuesserResult | None,
) -> PanelReport:
    packet_by_stage: dict[str, StagePacket] = {packet.stage: packet for packet in packets}
    canary_by_code: dict[str, str] = canaries(game)
    valid: list[ValidSolver] = []
    invalid: list[InvalidSolver] = []
    for result in solver_results:
        reason: str | None = invalid_reason(result, packet_by_stage, canary_by_code)
        if reason is not None:
            invalid.append(InvalidSolver(solver=result.solver, stage=result.stage, reason=reason))
            continue
        packet: StagePacket = packet_by_stage[result.stage]
        valid.append(ValidSolver(result=result, packet=packet, comparable_packet=normalize_quote_text(packet.text)))
    guesses: dict[str, str] = {}
    if guesser_result is not None:
        guesses = {guess.code: normalize_answer(guess.answer, game.config.language) for guess in guesser_result.guesses}
    puzzles: list[ItemVerdict] = []
    for position, puzzle in enumerate(ordered_puzzles(game)):
        gold: frozenset[str] = frozenset(puzzle.accepted_normalized)
        attempts: list[Attempt] = [
            puzzle_attempt(solver, puzzle.code, gold, game.config.language)
            for solver in valid
            if puzzle.code in solver.packet.codes
        ]
        guessable: bool = guesses.get(puzzle.code, "") in gold
        # The first puzzle teaches how the game works, so it may state its method.
        puzzles.append(judge_item(puzzle.code, puzzle.source.difficulty, attempts, gold, guessable, position > 0))
    questions: list[ItemVerdict] = []
    if game.story.deduction is not None:
        for question in game.story.deduction.questions:
            attempts = [
                question_attempt(solver, question) for solver in valid if question.id in solver.packet.questions
            ]
            gold = frozenset({question.correct.casefold()})
            questions.append(
                judge_item(question.id, QUESTION_DIFFICULTY, attempts, gold, guessable=False, can_be_trivial=False)
            )
    ok: bool = all(item.verdict == "pass" for item in [*puzzles, *questions])
    return PanelReport(ok=ok, puzzles=puzzles, questions=questions, invalid_solvers=invalid)


def invalid_reason(
    result: SolverResult, packet_by_stage: dict[str, StagePacket], canary_by_code: dict[str, str]
) -> str | None:
    if result.status == "failed":
        return "The solver failed."
    if result.stage not in packet_by_stage:
        return f"No packet exists for stage {result.stage}."
    output: list[str] = [value.casefold() for value in strings_of(result.model_dump())]
    for code, canary in canary_by_code.items():
        if any(canary.casefold() in value for value in output):
            return f"The output holds the canary of {code}, so the solver read the source files."
    return None


def strings_of(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_of(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_of(item)


def evidence_verified(evidence: list[Evidence], comparable_packet: str) -> bool:
    """True when there is evidence and every quote occurs in the packet. `comparable_packet` is a `comparable_text`."""
    if not evidence:
        return False
    for item in evidence:
        # Solvers often wrap a quote in quote marks that are not part of the document.
        quote: str = normalize_quote_text(item.quote).strip("\"' ")
        if not quote or quote not in comparable_packet:
            return False
    return True


def puzzle_attempt(solver: ValidSolver, code: str, gold: frozenset[str], language: str) -> Attempt:
    answer = next((answer for answer in solver.result.answers if answer.code == code), None)
    if answer is None:
        return Attempt(solver.result.solver, "", "", False, False, True, "no answer given", ())
    normalized: str = normalize_answer(answer.answer, language)
    return Attempt(
        solver=solver.result.solver,
        raw=answer.answer,
        normalized=normalized,
        correct=normalized in gold,
        verified=evidence_verified(answer.evidence, solver.comparable_packet),
        stuck=answer.stuck or not normalized,
        reasoning=answer.reasoning,
        candidates=tuple((normalize_answer(candidate.answer, language), candidate) for candidate in answer.candidates),
        all_steps_stated=answer.all_steps_stated,
        aha=answer.aha,
    )


def question_attempt(solver: ValidSolver, question: AccusationQuestion) -> Attempt:
    choice = next((choice for choice in solver.result.accusation if choice.question == question.id), None)
    if choice is None:
        return Attempt(solver.result.solver, "", "", False, False, True, "no option chosen", ())
    normalized: str = choice.option.strip().casefold()
    return Attempt(
        solver=solver.result.solver,
        raw=choice.option,
        normalized=normalized,
        correct=normalized == question.correct.casefold(),
        verified=evidence_verified(choice.evidence, solver.comparable_packet),
        stuck=not normalized,
        reasoning="",
        candidates=(),
    )


def required_solves(difficulty: Difficulty, solvers: int) -> int | None:
    if solvers < MIN_SOLVERS:
        return None
    small_panel, full_panel = REQUIRED_SOLVES[difficulty]
    return full_panel if solvers >= FULL_PANEL else small_panel


def judge_item(
    code: str,
    difficulty: Difficulty,
    attempts: list[Attempt],
    gold: frozenset[str],
    guessable: bool,
    can_be_trivial: bool,
) -> ItemVerdict:
    required: int | None = required_solves(difficulty, len(attempts))
    solved: list[Attempt] = [attempt for attempt in attempts if attempt.correct and attempt.verified]
    solves: int = len(solved)
    stated: list[Attempt] = [attempt for attempt in solved if attempt.all_steps_stated]
    wrong_attempts: list[Attempt] = [attempt for attempt in attempts if attempt.normalized and not attempt.correct]
    wrong: list[AnswerCount] = answer_counts(wrong_attempts)
    alternatives: list[Alternative] = find_alternatives(attempts, wrong_attempts, gold)
    verified_wrong: list[AnswerCount] = answer_counts([attempt for attempt in wrong_attempts if attempt.verified])
    suspect: AnswerCount | None = next(
        (answer for answer in verified_wrong if answer.count >= GOLD_SUSPECT_AGREEMENT), None
    )
    verdict: Verdict
    notes: list[str]
    if required is None:
        verdict, notes = "insufficient_solvers", [f"Only {len(attempts)} valid solvers got this item."]
    elif suspect is not None:
        verdict = "gold_suspect"
        agreement: str = f"{suspect.count} solvers agree on '{suspect.answer}' with verified evidence."
        notes = [f"{agreement} Check the official answer first."]
    elif alternatives:
        verdict, notes = "ambiguous", []
    elif guessable:
        verdict, notes = "guessable", ["The guesser found the answer without the documents."]
    elif can_be_trivial and stated and 2 * len(stated) >= solves:
        verdict = "trivial"
        notes = [f"{attempt.solver}: the material states every step; aha: {attempt.aha}" for attempt in stated]
    elif solves < required:
        verdict = "too_hard"
        notes = [attempt_note(attempt) for attempt in attempts if not (attempt.correct and attempt.verified)]
    else:
        verdict, notes = "pass", []
    return ItemVerdict(
        code=code,
        verdict=verdict,
        solvers=len(attempts),
        required=required,
        solves_verified=solves,
        guesses=sum(1 for attempt in attempts if attempt.correct and not attempt.verified),
        wrong=wrong,
        alternatives=alternatives,
        guessable=guessable,
        steps_stated=len(stated),
        notes=notes,
    )


def answer_counts(attempts: list[Attempt]) -> list[AnswerCount]:
    counts: Counter[str] = Counter(attempt.normalized for attempt in attempts)
    first_text: dict[str, str] = {}
    for attempt in attempts:
        first_text.setdefault(attempt.normalized, attempt.raw)
    return [AnswerCount(answer=first_text[answer], count=count) for answer, count in counts.most_common()]


def find_alternatives(
    attempts: list[Attempt], wrong_attempts: list[Attempt], gold: frozenset[str]
) -> list[Alternative]:
    """Return the wrong answers that 2 or more solvers share, and the candidates that a proven solver says fit."""
    shared: Counter[str] = Counter(attempt.normalized for attempt in wrong_attempts)
    fitting: Counter[str] = Counter()
    texts: dict[str, str] = {attempt.normalized: attempt.raw for attempt in reversed(wrong_attempts)}
    for attempt in attempts:
        if not attempt.verified:
            continue
        for normalized, candidate in attempt.candidates:
            if candidate.fits_all_clues and normalized and normalized not in gold:
                fitting[normalized] += 1
                texts.setdefault(normalized, candidate.answer)
    answers: list[str] = [answer for answer, count in shared.most_common() if count >= SHARED_WRONG_ANSWER]
    answers += [answer for answer in fitting if answer not in answers]
    return [
        Alternative(
            answer=texts[answer], count=shared[answer] + fitting[answer], notes=alternative_notes(answer, attempts)
        )
        for answer in answers
    ]


def alternative_notes(answer: str, attempts: list[Attempt]) -> list[str]:
    notes: list[str] = [
        f"{attempt.solver}: {attempt.reasoning}" for attempt in attempts if attempt.normalized == answer
    ]
    for attempt in attempts:
        for normalized, candidate in attempt.candidates:
            if normalized != answer:
                continue
            if candidate.fits_all_clues and attempt.verified:
                notes.append(f"{attempt.solver}: fits every clue")
            elif candidate.failing_clue:
                notes.append(f"{attempt.solver} rules it out: {candidate.failing_clue}")
    return notes


def attempt_note(attempt: Attempt) -> str:
    if attempt.correct:
        action: str = "correct but without verified evidence"
    elif attempt.stuck:
        action = "stuck"
    else:
        action = f"answered '{attempt.raw}'"
    return f"{attempt.solver}: {action}: {attempt.reasoning}" if attempt.reasoning else f"{attempt.solver}: {action}"


def report_summary(report: PanelReport) -> dict[str, Any]:
    """Return a summary small enough for the one JSON line that a CLI verb prints."""
    items: list[ItemVerdict] = [*report.puzzles, *report.questions]
    failing: list[dict[str, str]] = [
        {"code": item.code, "reason": shorten(item_reason(item), MAX_REASON_LENGTH)}
        for item in items
        if item.verdict != "pass"
    ]
    summary: dict[str, Any] = {
        "ok": report.ok,
        "verdicts": dict(Counter(item.verdict for item in items)),
        "invalid_solvers": len(report.invalid_solvers),
        "failing": failing,
    }
    shown: int = len(failing)
    while len(json.dumps(summary).encode()) > SUMMARY_LIMIT_BYTES:
        shown -= 1
        summary["failing"] = failing[:shown]
        summary["more_failing"] = len(failing) - shown
    return summary


def item_reason(item: ItemVerdict) -> str:
    if item.verdict == "insufficient_solvers":
        return f"too few valid solvers: {item.solvers}, the panel needs {MIN_SOLVERS}"
    if item.verdict == "gold_suspect":
        return f"gold suspect: {item.notes[0]}"
    if item.verdict == "ambiguous":
        listed: str = ", ".join(
            f"'{shorten(alternative.answer, MAX_ANSWER_LENGTH)}' ({alternative.count})"
            for alternative in item.alternatives
        )
        return f"ambiguous: other answers fit: {listed}"
    if item.verdict == "guessable":
        return "guessable: the guesser found it without the documents"
    if item.verdict == "trivial":
        return f"trivial: {item.steps_stated} of {item.solves_verified} solvers say the material states every step"
    return f"too hard: {item.solves_verified} verified solves of {item.solvers}, needs {item.required}"


def shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."
