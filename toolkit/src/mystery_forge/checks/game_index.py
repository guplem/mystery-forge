"""Lookups that several checks share: models by id, stage positions, every clue with its file, and squashed text."""

from dataclasses import dataclass
from typing import Final

from mystery_forge.answers import normalize_answer
from mystery_forge.game import AssembledDocument, AssembledPuzzle, Game
from mystery_forge.spec.models import Clue

STORY_FILE: Final[str] = "story.yaml"
FLOW_FILE: Final[str] = "flow.yaml"
# Answer kinds that look like a code. Names and choices appear in the documents by design, so no leak check uses them.
CODE_LIKE_KINDS: Final[frozenset[str]] = frozenset({"word", "phrase", "number", "digits"})
# A shorter squashed answer occurs inside ordinary words by chance, so a substring search would find false leaks.
MIN_SEARCH_LENGTH: Final[int] = 4
# `normalize_answer` drops a leading article only for a known language. A text is not an answer: keep every word.
NO_LANGUAGE: Final[str] = ""


@dataclass(frozen=True)
class ClueEntry:
    """One clue with the file and the field path that define it. `puzzle` is None for a story clue."""

    clue: Clue
    file: str
    path: str
    puzzle: AssembledPuzzle | None


def squash(text: str) -> str:
    """Return the text as lowercase ASCII letters and digits only, so "B O A T" and "boat" compare equal."""
    return normalize_answer(text, NO_LANGUAGE)


def mentions(text: str, squashed_answer: str) -> bool:
    """Tell if a text contains a squashed answer. A short answer must match a whole word, not part of one."""
    if not squashed_answer:
        return False
    if len(squashed_answer) >= MIN_SEARCH_LENGTH:
        return squashed_answer in squash(text)
    return squashed_answer in {squash(word) for word in text.split()}


def stage_positions(game: Game) -> dict[str, int]:
    return {stage.id: index for index, stage in enumerate(game.flow.stages)}


def puzzles_by_id(game: Game) -> dict[str, AssembledPuzzle]:
    return {puzzle.source.id: puzzle for puzzle in game.puzzles}


def documents_by_id(game: Game) -> dict[str, AssembledDocument]:
    return {document.meta.id: document for document in game.documents}


def puzzles_in_code_order(game: Game) -> list[AssembledPuzzle]:
    """Sort the puzzles the way players meet them: by stage, then by the number of their code (A1, A2, B1)."""
    positions: dict[str, int] = stage_positions(game)

    def order(puzzle: AssembledPuzzle) -> tuple[int, int]:
        return positions.get(puzzle.source.stage, len(positions)), int(puzzle.code[1:])

    return sorted(game.puzzles, key=order)


def clue_entries(game: Game) -> list[ClueEntry]:
    entries: list[ClueEntry] = [
        ClueEntry(clue=clue, file=STORY_FILE, path=f"clues.{index}", puzzle=None)
        for index, clue in enumerate(game.story.clues)
    ]
    for puzzle in game.puzzles:
        entries.extend(
            ClueEntry(clue=clue, file=puzzle.file, path=f"clues.{index}", puzzle=puzzle)
            for index, clue in enumerate(puzzle.source.clues)
        )
    return entries


def clues_by_id(game: Game) -> dict[str, ClueEntry]:
    """Index the clues by id. With a duplicate id the first clue wins; the ledger check reports the duplicate."""
    index: dict[str, ClueEntry] = {}
    for entry in clue_entries(game):
        index.setdefault(entry.clue.id, entry)
    return index
