"""Shared helpers of the `test_checks_*` files: the assembled golden game and small model edits.

The checks read only the assembled `Game`, so most tests edit the model with `model_copy(update=...)`. That skips the
model validators on purpose: a check must also report states that only a broken source can produce.
"""

from collections.abc import Sequence
from functools import cache
from typing import Any

from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.assemble import assemble_game
from mystery_forge.catalog import Mechanic, load_mechanics
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledDocument, AssembledPuzzle, Game


@cache
def golden_game() -> Game:
    game: Game | None = assemble_game(GOLDEN_GAME, FAKE_IMPLEMENTATIONS).game
    assert game is not None
    return game


def golden_catalog() -> tuple[Mechanic, ...]:
    return load_mechanics()


def rules(findings: Sequence[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


def only_rule(findings: Sequence[Finding], rule: str) -> list[Finding]:
    return [finding for finding in findings if finding.rule == rule]


def edit_puzzle(game: Game, puzzle_id: str, **source_updates: Any) -> Game:
    """Change fields of one puzzle's source model."""
    puzzles: list[AssembledPuzzle] = [
        puzzle.model_copy(update={"source": puzzle.source.model_copy(update=source_updates)})
        if puzzle.source.id == puzzle_id
        else puzzle
        for puzzle in game.puzzles
    ]
    return game.model_copy(update={"puzzles": puzzles})


def edit_assembled_puzzle(game: Game, puzzle_id: str, **updates: Any) -> Game:
    """Change fields of one assembled puzzle, such as its artifact or its normalized answers."""
    puzzles: list[AssembledPuzzle] = [
        puzzle.model_copy(update=updates) if puzzle.source.id == puzzle_id else puzzle for puzzle in game.puzzles
    ]
    return game.model_copy(update={"puzzles": puzzles})


def edit_document(game: Game, document_id: str, meta: dict[str, Any] | None = None, **updates: Any) -> Game:
    """Change fields of one assembled document (`text`, `body_html`) and of its front matter (`meta`)."""
    documents: list[AssembledDocument] = []
    for document in game.documents:
        if document.meta.id == document_id:
            changes: dict[str, Any] = dict(updates)
            if meta is not None:
                changes["meta"] = document.meta.model_copy(update=meta)
            document = document.model_copy(update=changes)
        documents.append(document)
    return game.model_copy(update={"documents": documents})


def edit_story(game: Game, **updates: Any) -> Game:
    return game.model_copy(update={"story": game.story.model_copy(update=updates)})


def edit_flow(game: Game, **updates: Any) -> Game:
    return game.model_copy(update={"flow": game.flow.model_copy(update=updates)})


def edit_config(game: Game, section: str, **updates: Any) -> Game:
    """Change fields of one config section, such as `edit_config(game, "equipment", scissors=False)`."""
    changed_section: Any = getattr(game.config, section).model_copy(update=updates)
    return game.model_copy(update={"config": game.config.model_copy(update={section: changed_section})})


def golden_mechanics() -> dict[str, Mechanic]:
    return {mechanic.id: mechanic for mechanic in golden_catalog()}
