"""Variety and fit: catalog mechanics that suit the equipment and the audience, and a mix of player actions.

A game where every puzzle asks for the same action (decode, decode, decode) feels like homework. These rules come
from the catalog design guide (`catalog/design_rules.md`). The rules that the plan step shares (`plan.py`) are pure
functions over (puzzle id, mechanic) pairs in code order, so one definition serves both.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Final

from mystery_forge.catalog import Mechanic
from mystery_forge.checks.game_index import (
    ClueEntry,
    clues_by_id,
    puzzles_by_id,
    puzzles_in_code_order,
    stage_positions,
)
from mystery_forge.config import EquipmentConfig
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game

MIN_PLAYER_ACTIONS: Final[int] = 4
MAX_LOOKUP_CIPHERS: Final[int] = 2
MAX_SAME_MECHANIC: Final[int] = 2
MIN_CROSS_DOCUMENT_SHARE: Final[float] = 0.4
# A puzzle id with the catalog mechanic that it uses.
MechanicUse = tuple[str, Mechanic]


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
    uses: list[MechanicUse] = [(puzzle.source.id, mechanic) for puzzle, mechanic in known]
    by_id: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    return [
        *findings,
        *player_action_findings(uses, len(ordered)),
        *lookup_cipher_findings(uses),
        *same_action_findings(uses, by_id),
        *repeated_mechanic_findings(uses),
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


def lookup_cipher_ids(uses: Sequence[MechanicUse]) -> list[str]:
    """Return the ids of the lookup ciphers when there are more than a game allows, else nothing."""
    lookups: list[str] = [puzzle_id for puzzle_id, mechanic in uses if mechanic.lookup_cipher]
    return lookups if len(lookups) > MAX_LOOKUP_CIPHERS else []


def overused_mechanics(uses: Sequence[MechanicUse]) -> dict[str, int]:
    """Map each mechanic that more puzzles use than a game allows to its count."""
    counts: Counter[str] = Counter(mechanic.id for _, mechanic in uses)
    return {mechanic_id: count for mechanic_id, count in counts.items() if count > MAX_SAME_MECHANIC}


def missing_player_actions(uses: Sequence[MechanicUse], puzzle_count: int) -> int | None:
    """Return the number of different player actions that the game needs when it has fewer, else None."""
    wanted: int = min(MIN_PLAYER_ACTIONS, puzzle_count)
    return wanted if len({mechanic.player_action for _, mechanic in uses}) < wanted else None


def same_action_pairs(uses: Sequence[MechanicUse]) -> list[tuple[str, str]]:
    """Return each pair of puzzles in a row, in code order, that ask for the same player action."""
    return [
        (previous_id, puzzle_id)
        for (previous_id, previous), (puzzle_id, mechanic) in pairwise(uses)
        if previous.player_action == mechanic.player_action
    ]


def player_action_findings(uses: Sequence[MechanicUse], puzzle_count: int) -> list[Finding]:
    wanted: int | None = missing_player_actions(uses, puzzle_count)
    if wanted is None:
        return []
    actions: list[str] = sorted({mechanic.player_action for _, mechanic in uses})
    return [
        Finding(
            severity="warning",
            rule="variety.player_actions",
            message=f"The puzzles use {len(actions)} kinds of player action ({', '.join(actions)}); the game "
            f"needs at least {wanted}.",
            fix_hint="Swap a puzzle for a mechanic with another player action, such as search, logic, or spatial.",
        )
    ]


def lookup_cipher_findings(uses: Sequence[MechanicUse]) -> list[Finding]:
    lookups: list[str] = lookup_cipher_ids(uses)
    if not lookups:
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


def same_action_findings(uses: Sequence[MechanicUse], puzzles: Mapping[str, AssembledPuzzle]) -> list[Finding]:
    actions: dict[str, str] = {puzzle_id: mechanic.player_action for puzzle_id, mechanic in uses}
    return [
        Finding(
            severity="warning",
            rule="variety.same_action_in_a_row",
            message=f"{puzzles[puzzle_id].code} ({puzzle_id}) asks for the same player action as "
            f"{puzzles[previous_id].code} ({actions[puzzle_id]}).",
            file=puzzles[puzzle_id].file,
            path="mechanic",
            fix_hint="Alternate the player actions, or move one of the two puzzles.",
        )
        for previous_id, puzzle_id in same_action_pairs(uses)
    ]


def repeated_mechanic_findings(uses: Sequence[MechanicUse]) -> list[Finding]:
    return [
        Finding(
            severity="warning",
            rule="variety.repeated_mechanic",
            message=f"{count} puzzles use the mechanic '{mechanic_id}'; a game uses one mechanic at most "
            f"{MAX_SAME_MECHANIC} times.",
            fix_hint="Replace one of these puzzles with another mechanic.",
        )
        for mechanic_id, count in overused_mechanics(uses).items()
    ]


def final_puzzle_findings(game: Game) -> list[Finding]:
    """A final meta puzzle pulls the game together: it uses earlier answers, one of each envelope at least."""
    final: AssembledPuzzle | None = puzzles_by_id(game).get(game.flow.final_puzzle or "")
    if final is None:
        return []
    findings: list[Finding] = []
    if not final.source.is_meta and len(final.source.depends_on) < 2:
        findings.append(
            Finding(
                severity="warning",
                rule="variety.final_not_meta",
                message=f"The final puzzle {final.source.id} is not a meta puzzle and depends on fewer than 2 "
                "puzzles, so the ending does not pull the game together.",
                file=final.file,
                path="is_meta",
                fix_hint="Make the final puzzle use the answers of 2 or more earlier puzzles, and set is_meta to true.",
            )
        )
    missing: list[str] = stages_without_dependency(game, final)
    if game.config.format != "case_file" and missing:
        findings.append(
            Finding(
                severity="warning",
                rule="variety.final_not_meta",
                message=f"The final puzzle {final.source.id} uses no answer of the stages {', '.join(missing)}, so "
                "players never bring those envelopes together.",
                file=final.file,
                path="depends_on",
                fix_hint="Add a puzzle of each earlier stage to depends_on of the final puzzle, and let the final "
                "material combine their answers.",
            )
        )
    return findings


def stages_without_dependency(game: Game, final: AssembledPuzzle) -> list[str]:
    """Return the stages before the final puzzle's stage that no direct dependency of the final puzzle comes from."""
    final_position: int = stage_positions(game).get(final.source.stage, 0)
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    used: set[str] = {puzzles[item].source.stage for item in final.source.depends_on if item in puzzles}
    return [stage.id for stage in game.flow.stages[:final_position] if stage.id not in used]


def cross_document_findings(game: Game) -> list[Finding]:
    if not game.puzzles:
        return []
    clues: dict[str, ClueEntry] = clues_by_id(game)
    combining: int = 0
    for puzzle in game.puzzles:
        # A hidden clue has no document, so it adds no document to combine.
        cited: set[str | None] = {
            clues[clue_id].clue.document for step in puzzle.source.solution for clue_id in step.uses if clue_id in clues
        } - {None}
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
