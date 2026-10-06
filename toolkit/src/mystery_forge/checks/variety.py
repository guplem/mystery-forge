"""Variety and fit: catalog mechanics that suit the equipment and the audience, and a mix of player actions.

A game where every puzzle asks for the same action (decode, decode, decode) feels like homework. These rules come
from the catalog design guide (`catalog/design_rules.md`).
"""

from collections import Counter
from collections.abc import Mapping
from itertools import pairwise
from typing import Final

from mystery_forge.catalog import Mechanic
from mystery_forge.checks.game_index import ClueEntry, clues_by_id, puzzles_by_id, puzzles_in_code_order
from mystery_forge.config import EquipmentConfig
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game

MIN_PLAYER_ACTIONS: Final[int] = 4
MAX_LOOKUP_CIPHERS: Final[int] = 2
MAX_SAME_MECHANIC: Final[int] = 2
MIN_CROSS_DOCUMENT_SHARE: Final[float] = 0.4


def check_variety(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    ordered: list[AssembledPuzzle] = puzzles_in_code_order(game)
    findings: list[Finding] = []
    known: list[tuple[AssembledPuzzle, Mechanic]] = []
    for puzzle in ordered:
        mechanic: Mechanic | None = mechanics.get(puzzle.source.mechanic)
        if mechanic is None:
            findings.append(unknown_mechanic_finding(puzzle))
            continue
        known.append((puzzle, mechanic))
        findings.extend(equipment_findings(game, puzzle, mechanic))
        if game.config.audience not in mechanic.audiences:
            findings.append(audience_finding(game, puzzle))
    return [
        *findings,
        *player_action_findings(known, len(ordered)),
        *lookup_cipher_findings(known),
        *same_action_findings(known),
        *repeated_mechanic_findings(known),
        *final_puzzle_findings(game),
        *cross_document_findings(game),
    ]


def unknown_mechanic_finding(puzzle: AssembledPuzzle) -> Finding:
    return Finding(
        severity="error",
        rule="variety.unknown_mechanic",
        message=f"The mechanic '{puzzle.source.mechanic}' of {puzzle.source.id} is not in the catalog.",
        file=puzzle.file,
        path="mechanic",
        fix_hint="Pick a mechanic id from `forge catalog list`.",
    )


def equipment_findings(game: Game, puzzle: AssembledPuzzle, mechanic: Mechanic) -> list[Finding]:
    equipment: EquipmentConfig = game.config.equipment
    missing: list[str] = [
        need
        for need, required, available in (
            ("scissors", mechanic.needs.scissors, equipment.scissors),
            ("tape or glue", mechanic.needs.tape, equipment.tape_or_glue),
            ("a color printer", mechanic.needs.color, equipment.printer == "color"),
        )
        if required and not available
    ]
    return [
        Finding(
            severity="error",
            rule="variety.equipment",
            message=f"The mechanic '{mechanic.id}' of {puzzle.source.id} needs {need}, which the players do not have.",
            file=puzzle.file,
            path="mechanic",
            fix_hint="Pick a mechanic that fits the equipment in config.json: `forge catalog list` shows the needs.",
        )
        for need in missing
    ]


def audience_finding(game: Game, puzzle: AssembledPuzzle) -> Finding:
    return Finding(
        severity="warning",
        rule="variety.audience",
        message=f"The mechanic '{puzzle.source.mechanic}' of {puzzle.source.id} does not suit the audience "
        f"'{game.config.audience}'.",
        file=puzzle.file,
        path="mechanic",
        fix_hint="Pick a mechanic whose catalog audiences include the game's audience.",
    )


def player_action_findings(known: list[tuple[AssembledPuzzle, Mechanic]], puzzle_count: int) -> list[Finding]:
    actions: set[str] = {mechanic.player_action for _, mechanic in known}
    wanted: int = min(MIN_PLAYER_ACTIONS, puzzle_count)
    if len(actions) >= wanted:
        return []
    return [
        Finding(
            severity="warning",
            rule="variety.player_actions",
            message=f"The puzzles use {len(actions)} kinds of player action ({', '.join(sorted(actions))}); the game "
            f"needs at least {wanted}.",
            fix_hint="Swap a puzzle for a mechanic with another player action, such as search, logic, or spatial.",
        )
    ]


def lookup_cipher_findings(known: list[tuple[AssembledPuzzle, Mechanic]]) -> list[Finding]:
    lookups: list[str] = [puzzle.source.id for puzzle, mechanic in known if mechanic.lookup_cipher]
    if len(lookups) <= MAX_LOOKUP_CIPHERS:
        return []
    return [
        Finding(
            severity="error",
            rule="variety.lookup_ciphers",
            message=f"{len(lookups)} puzzles are lookup ciphers ({', '.join(lookups)}); a game allows at most "
            f"{MAX_LOOKUP_CIPHERS}.",
            fix_hint="Replace a lookup cipher with a mechanic of another kind.",
        )
    ]


def same_action_findings(known: list[tuple[AssembledPuzzle, Mechanic]]) -> list[Finding]:
    return [
        Finding(
            severity="warning",
            rule="variety.same_action_in_a_row",
            message=f"{puzzle.code} ({puzzle.source.id}) asks for the same player action as {previous.code} "
            f"({mechanic.player_action}).",
            file=puzzle.file,
            path="mechanic",
            fix_hint="Alternate the player actions, or move one of the two puzzles.",
        )
        for (previous, previous_mechanic), (puzzle, mechanic) in pairwise(known)
        if previous_mechanic.player_action == mechanic.player_action
    ]


def repeated_mechanic_findings(known: list[tuple[AssembledPuzzle, Mechanic]]) -> list[Finding]:
    counts: Counter[str] = Counter(mechanic.id for _, mechanic in known)
    return [
        Finding(
            severity="warning",
            rule="variety.repeated_mechanic",
            message=f"{count} puzzles use the mechanic '{mechanic_id}'; a game uses one mechanic at most "
            f"{MAX_SAME_MECHANIC} times.",
            fix_hint="Replace one of these puzzles with another mechanic.",
        )
        for mechanic_id, count in counts.items()
        if count > MAX_SAME_MECHANIC
    ]


def final_puzzle_findings(game: Game) -> list[Finding]:
    final: AssembledPuzzle | None = puzzles_by_id(game).get(game.flow.final_puzzle or "")
    if final is None or final.source.is_meta or len(final.source.depends_on) >= 2:
        return []
    return [
        Finding(
            severity="warning",
            rule="variety.final_not_meta",
            message=f"The final puzzle {final.source.id} is not a meta puzzle and depends on fewer than 2 puzzles, "
            "so the ending does not pull the game together.",
            file=final.file,
            path="is_meta",
            fix_hint="Make the final puzzle use the answers of 2 or more earlier puzzles, and set is_meta to true.",
        )
    ]


def cross_document_findings(game: Game) -> list[Finding]:
    if not game.puzzles:
        return []
    clues: dict[str, ClueEntry] = clues_by_id(game)
    combining: int = 0
    for puzzle in game.puzzles:
        cited: set[str] = {
            clues[clue_id].clue.document for step in puzzle.source.solution for clue_id in step.uses if clue_id in clues
        }
        combining += len(cited) >= 2
    if combining / len(game.puzzles) >= MIN_CROSS_DOCUMENT_SHARE:
        return []
    return [
        Finding(
            severity="warning",
            rule="variety.cross_document",
            message=f"Only {combining} of {len(game.puzzles)} puzzles cite clues from 2 or more documents; at "
            f"least {MIN_CROSS_DOCUMENT_SHARE:.0%} should.",
            fix_hint="Let more puzzles combine documents, such as a key in one document and the code in another.",
        )
    ]
