"""The paper answer check: an alphabetical register of answers that points to shuffled, numbered result paragraphs.

Players look up their answer in the register and read the paragraph that it points to. The register lists the real
answers next to near misses and decoys with the same look, so a glance at it does not reveal which entries are
real. Every entry gets its own paragraph, because entries that share a paragraph would give the wrong ones away.
"""

import random
import unicodedata
from dataclasses import dataclass
from typing import Final, Literal

from mystery_forge.answers import normalize_answer
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.i18n import text

Outcome = Literal["correct", "near_miss", "wrong"]
DIGIT_DECOY_COUNT: Final[int] = 3
PARAGRAPH_NUMBERS: Final[range] = range(100, 1000)


@dataclass(frozen=True)
class RegisterEntry:
    text: str
    paragraph: int


@dataclass(frozen=True)
class ResultParagraph:
    number: int
    outcome: Outcome
    message: str
    action: str
    reveals: str
    # A paragraph too long for one column goes on in a second part with the same number.
    continued: bool = False


@dataclass(frozen=True)
class AnswerRegister:
    entries: list[RegisterEntry]
    paragraphs: list[ResultParagraph]


@dataclass(frozen=True)
class Candidate:
    text: str
    outcome: Outcome
    message: str
    action: str = ""
    reveals: str = ""


def register_sort_key(entry_text: str) -> tuple[int, int, str]:
    """Numbers first, in numeric order; then words in alphabetical order, with accents ignored."""
    compact: str = entry_text.replace(" ", "")
    if compact.isdigit():
        return (0, int(compact), entry_text)
    plain: str = "".join(
        character for character in unicodedata.normalize("NFKD", entry_text) if not unicodedata.combining(character)
    )
    return (1, 0, plain.casefold())


def correct_action(game: Game, puzzle: AssembledPuzzle) -> str:
    language: str = game.config.language
    for stage in game.flow.stages:
        if stage.opens_with == puzzle.source.id:
            return text(language, "register_open_envelope", envelope=text(language, "envelope_label", stage=stage.id))
    if puzzle.source.id == game.flow.final_puzzle:
        return text(language, "register_go_accusation" if game.flow.accusation else "register_case_solved")
    return text(language, "register_keep_answer")


def plausible_decoys(game: Game, puzzle: AssembledPuzzle, rng: random.Random) -> list[str]:
    """Wrong entries that look like real answers: other names for a name, other codes of the same length for digits."""
    source = puzzle.source
    language: str = game.config.language
    answers: set[str] = {normalize_answer(item, language) for item in (source.answer, *source.accepted)}
    if source.answer_format.kind == "name":
        return [
            character.name
            for character in game.story.characters
            if not any(answer in normalize_answer(character.name, language) for answer in answers)
        ]
    if source.answer.isdigit():
        length: int = len(source.answer)
        return [f"{rng.randrange(10**length):0{length}d}" for _ in range(DIGIT_DECOY_COUNT)]
    return []


def register_candidates(game: Game, rng: random.Random) -> list[Candidate]:
    """Every entry, in priority order: correct answers, then near misses, then decoys."""
    language: str = game.config.language
    correct: list[Candidate] = []
    near: list[Candidate] = []
    wrong: list[Candidate] = []
    wrong_message: str = text(language, "register_wrong")
    for puzzle in game.puzzles:
        source = puzzle.source
        message: str = text(language, "register_correct", code=puzzle.code)
        action: str = correct_action(game, puzzle)
        correct.extend(
            Candidate(item, "correct", message, action, source.reveals) for item in (source.answer, *source.accepted)
        )
        near.extend(Candidate(miss.answer, "near_miss", miss.message) for miss in source.near_misses)
        decoys: list[str] = [*source.decoys, *plausible_decoys(game, puzzle, rng)]
        wrong.extend(Candidate(decoy, "wrong", wrong_message) for decoy in decoys)
    return [*correct, *near, *wrong]


def build_answer_register(game: Game) -> AnswerRegister:
    rng: random.Random = random.Random(f"{game.brief.seed}:answer-register")
    # Two spellings of one correct answer ("LOW TIDE", "THE LOW TIDE") both stay, to make the lookup easy. A wrong
    # entry that normalizes like an earlier entry is dropped, so the register never calls a correct answer wrong.
    shown: set[str] = set()
    claimed: set[str] = set()
    unique: list[Candidate] = []
    for candidate in register_candidates(game, rng):
        display: str = candidate.text.strip().upper()
        key: str = normalize_answer(candidate.text, game.config.language)
        if display in shown or (candidate.outcome != "correct" and key in claimed):
            continue
        shown.add(display)
        claimed.add(key)
        unique.append(candidate)
    numbers: list[int] = rng.sample(PARAGRAPH_NUMBERS, len(unique))
    entries: list[RegisterEntry] = [
        RegisterEntry(text=candidate.text.strip().upper(), paragraph=number)
        for candidate, number in zip(unique, numbers, strict=True)
    ]
    paragraphs: list[ResultParagraph] = [
        ResultParagraph(number, candidate.outcome, candidate.message, candidate.action, candidate.reveals)
        for candidate, number in zip(unique, numbers, strict=True)
    ]
    return AnswerRegister(
        entries=sorted(entries, key=lambda entry: register_sort_key(entry.text)),
        paragraphs=sorted(paragraphs, key=lambda paragraph: paragraph.number),
    )
