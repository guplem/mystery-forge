"""The typed results of the solver panel and the verdicts of the judge.

The pskill workflow gives each solver task an output schema that mirrors `SolverResult`, so the field names stay short
and plain. Unknown fields are errors: a solver that adds a field must not hide text from the canary check.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Verdict = Literal["pass", "ambiguous", "gold_suspect", "too_hard", "guessable", "trivial", "insufficient_solvers"]
SolverStatus = Literal["done", "failed"]


class PanelModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidence(PanelModel):
    # The document title as the packet prints it.
    document: str
    # The words of the document, copied exactly.
    quote: str


class Candidate(PanelModel):
    """Another answer that the solver considered."""

    answer: str
    fits_all_clues: bool = False
    # The clue that rules this answer out; empty when it fits every clue.
    failing_clue: str = ""


class SolverAnswer(PanelModel):
    code: str
    # Empty when the solver is stuck.
    answer: str = ""
    stuck: bool = False
    candidates: list[Candidate] = []
    evidence: list[Evidence] = []
    reasoning: str = ""
    # The one insight that unlocked the puzzle.
    aha: str = ""
    # True when the material stated every step of the method, so solving it took no insight.
    all_steps_stated: bool = False


class AccusationChoice(PanelModel):
    question: str
    option: str
    evidence: list[Evidence] = []


class SolverResult(PanelModel):
    solver: str
    stage: str
    answers: list[SolverAnswer] = []
    accusation: list[AccusationChoice] = []
    # A solver that could not work returns "failed": pskill pauses the whole run on a failed task.
    status: SolverStatus = "done"


class Guess(PanelModel):
    code: str
    answer: str


class GuesserResult(PanelModel):
    guesses: list[Guess] = []


class AnswerCount(PanelModel):
    # The text of the first solver that gave this answer; the count groups answers by their normalized form.
    answer: str
    count: int


class Alternative(PanelModel):
    """A wrong answer that also fits, so players could defend it."""

    answer: str
    count: int
    # Each solver's reasoning for it, or the clue that a solver says rules it out.
    notes: list[str]


class ItemVerdict(PanelModel):
    """The verdict on one puzzle (by its code) or on one accusation question (by its id)."""

    code: str
    verdict: Verdict
    # The valid solvers that got this item.
    solvers: int
    # The verified solves that a pass needs; None when too few valid solvers took part.
    required: int | None
    solves_verified: int
    # Correct answers without verified evidence.
    guesses: int
    wrong: list[AnswerCount]
    alternatives: list[Alternative]
    guessable: bool
    # The verified solvers that say the material states every step of the method.
    steps_stated: int = 0
    notes: list[str]


class InvalidSolver(PanelModel):
    solver: str
    stage: str
    reason: str


class PanelReport(PanelModel):
    ok: bool
    puzzles: list[ItemVerdict]
    questions: list[ItemVerdict]
    invalid_solvers: list[InvalidSolver]
