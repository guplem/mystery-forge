"""The paper answer check: an alphabetical register of answers that points to shuffled, numbered result paragraphs.

Players look up their answer in the register and read the paragraph that it points to. The register sits on the
table from the start, so it must not give the real answers away. Every entry has one printed form (capital letters
and digits only), and every real answer hides among decoys of the same shape: codes with the same digit count, or
words with about the same letter count. Every entry gets its own paragraph, because entries that share a paragraph
would give the wrong ones away. A correct paragraph says only what to do next, never story text.
"""

import random
import unicodedata
from dataclasses import dataclass
from itertools import pairwise
from typing import Final, Literal

from mystery_forge.answers import normalize_answer
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.i18n import text

Outcome = Literal["correct", "near_miss", "wrong"]
PARAGRAPH_NUMBERS: Final[range] = range(100, 1000)
# Each real entry needs this many other entries of the same shape, so that a glance cannot pick it out.
SAME_SHAPE_NEIGHBORS: Final[int] = 4
# A word decoy may have this many letters more or fewer than the real answer.
LETTER_COUNT_SPREAD: Final[int] = 2


@dataclass(frozen=True)
class RegisterEntry:
    text: str
    paragraph: int


@dataclass(frozen=True)
class ResultParagraph:
    number: int
    outcome: Outcome
    message: str
    # A paragraph too long for one column goes on in a second part with the same number.
    continued: bool = False


@dataclass(frozen=True)
class AnswerRegister:
    entries: list[RegisterEntry]
    paragraphs: list[ResultParagraph]


@dataclass(frozen=True)
class Candidate:
    form: str
    outcome: Outcome
    message: str


def register_form(answer: str) -> str:
    """The printed form of an entry: capital letters and digits, without spaces, accents, or punctuation."""
    # No language: a leading article stays, because the players write exactly what they see.
    return normalize_answer(answer, "").upper()


def same_shape(form: str, other: str) -> bool:
    """Digits match digits of the same count; words match words with about the same letter count."""
    if form.isdigit():
        return other.isdigit() and len(other) == len(form)
    return not other.isdigit() and abs(len(other) - len(form)) <= LETTER_COUNT_SPREAD


def register_sort_key(entry_text: str) -> tuple[int, int, str]:
    """Numbers first, in numeric order; then words in alphabetical order, with accents ignored."""
    compact: str = entry_text.replace(" ", "")
    if compact.isdigit():
        return (0, int(compact), entry_text)
    plain: str = "".join(
        character for character in unicodedata.normalize("NFKD", entry_text) if not unicodedata.combining(character)
    )
    return (1, 0, plain.casefold())


def correct_message(game: Game, puzzle: AssembledPuzzle) -> str:
    language: str = game.config.language
    puzzle_id: str = puzzle.source.id
    for stage in game.flow.stages:
        if stage.opens_with == puzzle_id:
            return text(language, "register_correct_open", envelope=text(language, "envelope_label", stage=stage.id))
    if any(puzzle_id in other.source.depends_on for other in game.puzzles):
        return text(language, "register_correct_keep")
    if puzzle_id == game.flow.final_puzzle and game.flow.accusation:
        return text(language, "register_correct_accusation")
    return text(language, "register_correct_notes")


def name_decoys(game: Game, puzzle: AssembledPuzzle) -> list[str]:
    """For a name answer, the other character names, except a name that holds the answer."""
    source = puzzle.source
    if source.answer_format.kind != "name":
        return []
    language: str = game.config.language
    answers: set[str] = {normalize_answer(item, language) for item in (source.answer, *source.accepted)}
    return [
        character.name
        for character in game.story.characters
        if not any(answer in normalize_answer(character.name, language) for answer in answers)
    ]


def document_phrases(game: Game) -> list[str]:
    """The words and the word pairs of the document texts, in printed form, with letters only."""
    phrases: set[str] = set()
    for document in game.documents:
        for line in document.text.splitlines():
            words: list[str] = [register_form(word) for word in line.split()]
            phrases.update(words)
            phrases.update(first + second for first, second in pairwise(words))
    return sorted(phrase for phrase in phrases if phrase.isalpha())


class RegisterBuilder:
    """Collect the entries in priority order. A later entry never takes the form of an earlier one."""

    def __init__(self, language: str) -> None:
        self.language: str = language
        self.candidates: dict[str, Candidate] = {}
        # Every form that is correct, with and without a leading article, so no wrong entry can take it.
        self.correct_forms: set[str] = set()

    def is_free(self, answer: str) -> bool:
        form: str = register_form(answer)
        return bool(form) and form not in self.candidates and self.language_form(answer) not in self.correct_forms

    def language_form(self, answer: str) -> str:
        return normalize_answer(answer, self.language).upper()

    def add_correct(self, answer: str, message: str) -> None:
        for form in (register_form(answer), self.language_form(answer)):
            self.correct_forms.add(form)
            if form and form not in self.candidates:
                self.candidates[form] = Candidate(form, "correct", message)

    def add_wrong(self, answer: str, outcome: Outcome, message: str) -> None:
        if self.is_free(answer):
            self.candidates[register_form(answer)] = Candidate(register_form(answer), outcome, message)

    def missing_neighbors(self, form: str) -> int:
        count: int = sum(1 for other in self.candidates if other != form and same_shape(form, other))
        return max(0, SAME_SHAPE_NEIGHBORS - count)


def add_digit_decoys(builder: RegisterBuilder, form: str, message: str, rng: random.Random) -> None:
    # Fewer than the needed neighbors exist, so at least 10 - 5 codes of this length are still free: the loop ends.
    while builder.missing_neighbors(form):
        builder.add_wrong(f"{rng.randrange(10 ** len(form)):0{len(form)}d}", "wrong", message)


def add_word_decoys(builder: RegisterBuilder, form: str, message: str, phrases: list[str]) -> None:
    for phrase in phrases:
        if not builder.missing_neighbors(form):
            return
        if same_shape(form, phrase):
            builder.add_wrong(phrase, "wrong", message)


def register_candidates(game: Game, rng: random.Random) -> list[Candidate]:
    """Every entry: correct answers, then near misses, then the written decoys, then the decoys of the same shape."""
    language: str = game.config.language
    wrong_message: str = text(language, "register_wrong")
    builder = RegisterBuilder(language)
    for puzzle in game.puzzles:
        message: str = correct_message(game, puzzle)
        for answer in (puzzle.source.answer, *puzzle.source.accepted):
            builder.add_correct(answer, message)
    for puzzle in game.puzzles:
        for miss in puzzle.source.near_misses:
            builder.add_wrong(miss.answer, "near_miss", miss.message)
    for puzzle in game.puzzles:
        for decoy in (*puzzle.source.decoys, *name_decoys(game, puzzle)):
            builder.add_wrong(decoy, "wrong", wrong_message)
    phrases: list[str] = document_phrases(game)
    rng.shuffle(phrases)
    real_forms: list[str] = [form for form, candidate in builder.candidates.items() if candidate.outcome == "correct"]
    for form in real_forms:
        if form.isdigit():
            add_digit_decoys(builder, form, wrong_message, rng)
        else:
            add_word_decoys(builder, form, wrong_message, phrases)
    return list(builder.candidates.values())


def build_answer_register(game: Game) -> AnswerRegister:
    rng: random.Random = random.Random(f"{game.brief.seed}:answer-register")
    candidates: list[Candidate] = register_candidates(game, rng)
    numbers: list[int] = rng.sample(PARAGRAPH_NUMBERS, len(candidates))
    entries: list[RegisterEntry] = [
        RegisterEntry(text=candidate.form, paragraph=number)
        for candidate, number in zip(candidates, numbers, strict=True)
    ]
    paragraphs: list[ResultParagraph] = [
        ResultParagraph(number, candidate.outcome, candidate.message)
        for candidate, number in zip(candidates, numbers, strict=True)
    ]
    return AnswerRegister(
        entries=sorted(entries, key=lambda entry: register_sort_key(entry.text)),
        paragraphs=sorted(paragraphs, key=lambda paragraph: paragraph.number),
    )
