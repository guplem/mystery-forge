"""The puzzle graph: stages, dependencies, stage openings, reachability, the final puzzle, and artifact placement.

Players move through the game along this graph. A puzzle that depends on an unknown or a later puzzle, a stage that
never opens, an artifact that no document prints, or a text that an artifact needs and no document prints makes the
printed game impossible to finish.

The rules that the plan step shares (`plan.py`) are pure functions over `PuzzleNode`, so one definition serves both.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from mystery_forge.answers import normalize_answer
from mystery_forge.catalog import Mechanic
from mystery_forge.checks.game_index import FLOW_FILE, id_number, mentions, puzzles_by_id, squash, stage_positions
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.spec.documents import ARTIFACT_MARK
from mystery_forge.spec.models import Flow, Stage

DependencyIssueKind = Literal["unknown", "later_stage"]
OpenerIssueKind = Literal["unknown", "order"]
FinalPuzzleIssueKind = Literal["unknown", "stage"]


@dataclass(frozen=True)
class PuzzleNode:
    """The plain data of one puzzle that the graph rules read: a planned puzzle and a written puzzle both give it."""

    id: str
    stage: str
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class DependencyIssue:
    puzzle_id: str
    # The position of the dependency in the puzzle's depends_on list.
    index: int
    dependency_id: str
    kind: DependencyIssueKind


def check_graph(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    return [
        *unknown_stage_findings(game),
        *dependency_findings(game),
        *dependency_loop_findings(game),
        *stage_opening_findings(game),
        *reachability_findings(game),
        *final_puzzle_findings(game),
        *document_findings(game),
        *parallel_width_findings(game),
        *artifact_findings(game),
        *needed_text_findings(game),
        *unused_dependency_findings(game, mechanics),
    ]


def game_nodes(game: Game) -> list[PuzzleNode]:
    return [
        PuzzleNode(id=puzzle.source.id, stage=puzzle.source.stage, depends_on=tuple(puzzle.source.depends_on))
        for puzzle in game.puzzles
    ]


def dependency_issues(nodes: Sequence[PuzzleNode], stage_ids: Sequence[str]) -> list[DependencyIssue]:
    """Find each dependency on an unknown puzzle or on a puzzle of a later stage. An unknown stage is never later."""
    positions: dict[str, int] = {stage_id: index for index, stage_id in enumerate(stage_ids)}
    by_id: dict[str, PuzzleNode] = {node.id: node for node in nodes}
    issues: list[DependencyIssue] = []
    for node in nodes:
        for index, dependency_id in enumerate(node.depends_on):
            dependency: PuzzleNode | None = by_id.get(dependency_id)
            if dependency is None:
                issues.append(DependencyIssue(node.id, index, dependency_id, "unknown"))
            elif positions.get(dependency.stage, -1) > positions.get(node.stage, len(positions)):
                issues.append(DependencyIssue(node.id, index, dependency_id, "later_stage"))
    return issues


def stage_opener_issues(stages: Sequence[Stage], nodes: Sequence[PuzzleNode]) -> list[tuple[int, OpenerIssueKind]]:
    """Find each stage after the first that opens with an unknown puzzle or with a puzzle that is not earlier."""
    positions: dict[str, int] = {stage.id: index for index, stage in enumerate(stages)}
    by_id: dict[str, PuzzleNode] = {node.id: node for node in nodes}
    issues: list[tuple[int, OpenerIssueKind]] = []
    for index, stage in enumerate(stages[1:], start=1):
        opener: PuzzleNode | None = by_id.get(stage.opens_with)
        if opener is None:
            issues.append((index, "unknown"))
        elif positions.get(opener.stage, -1) >= index:
            issues.append((index, "order"))
    return issues


def final_puzzle_issue(flow: Flow, nodes: Sequence[PuzzleNode]) -> FinalPuzzleIssueKind | None:
    if flow.final_puzzle is None:
        return None
    final: PuzzleNode | None = next((node for node in nodes if node.id == flow.final_puzzle), None)
    if final is None:
        return "unknown"
    return "stage" if final.stage != flow.stages[-1].id else None


def unknown_stage_findings(game: Game) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    hint: str = f"Use one of the stage ids in flow.yaml: {', '.join(positions)}."
    findings: list[Finding] = [
        Finding(
            severity="error",
            rule="graph.unknown_stage",
            message=f"The puzzle {puzzle.source.id} is in the stage '{puzzle.source.stage}', which flow.yaml lacks.",
            file=puzzle.file,
            path="stage",
            fix_hint=hint,
        )
        for puzzle in game.puzzles
        if puzzle.source.stage not in positions
    ]
    findings.extend(
        Finding(
            severity="error",
            rule="graph.unknown_stage",
            message=f"The document {document.meta.id} is in the stage '{document.meta.stage}', which flow.yaml lacks.",
            file=document.file,
            path="stage",
            fix_hint=hint,
        )
        for document in game.documents
        if document.meta.stage not in positions
    )
    return findings


def dependency_findings(game: Game) -> list[Finding]:
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for issue in dependency_issues(game_nodes(game), list(stage_positions(game))):
        puzzle: AssembledPuzzle = puzzles[issue.puzzle_id]
        if issue.kind == "unknown":
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.unknown_dependency",
                    message=f"The puzzle {issue.puzzle_id} depends on {issue.dependency_id}, which does not exist.",
                    file=puzzle.file,
                    path=f"depends_on.{issue.index}",
                    fix_hint=f"Use an existing puzzle id: {', '.join(puzzles)}.",
                )
            )
        else:
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.dependency_later_stage",
                    message=f"The puzzle {issue.puzzle_id} in stage {puzzle.source.stage} depends on "
                    f"{issue.dependency_id} in the later stage {puzzles[issue.dependency_id].source.stage}.",
                    file=puzzle.file,
                    path=f"depends_on.{issue.index}",
                    fix_hint="Depend only on puzzles of the same or an earlier stage, or move one of the puzzles.",
                )
            )
    return findings


def transitive_dependencies(nodes: Sequence[PuzzleNode]) -> dict[str, set[str]]:
    """Map each puzzle id to every puzzle that it needs, directly or through other puzzles. Unknown ids drop out."""
    by_id: dict[str, PuzzleNode] = {node.id: node for node in nodes}
    needed: dict[str, set[str]] = {}
    for puzzle_id, node in by_id.items():
        found: set[str] = set()
        pending: list[str] = list(node.depends_on)
        while pending:
            dependency_id: str = pending.pop()
            if dependency_id in found or dependency_id not in by_id:
                continue
            found.add(dependency_id)
            pending.extend(by_id[dependency_id].depends_on)
        needed[puzzle_id] = found
    return needed


def dependency_loops(nodes: Sequence[PuzzleNode]) -> list[list[str]]:
    """Return each group of puzzles that depend on each other, every group in id order."""
    needed: dict[str, set[str]] = transitive_dependencies(nodes)
    in_loop: list[str] = sorted((puzzle_id for puzzle_id in needed if puzzle_id in needed[puzzle_id]), key=id_number)
    loops: list[list[str]] = []
    for puzzle_id in in_loop:
        loop: list[str] = [other for other in in_loop if other in needed[puzzle_id] and puzzle_id in needed[other]]
        if loop not in loops:
            loops.append(loop)
    return loops


def dependency_loop_findings(game: Game) -> list[Finding]:
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    return [
        Finding(
            severity="error",
            rule="graph.dependency_loop",
            message=f"The puzzles {', '.join(loop)} depend on each other in a loop, so players can never start them.",
            file=puzzles[loop[0]].file,
            path="depends_on",
            fix_hint="Remove one dependency of the loop. A puzzle can only depend on puzzles that players solve first.",
        )
        for loop in dependency_loops(game_nodes(game))
    ]


def stage_opening_findings(game: Game) -> list[Finding]:
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for index, kind in stage_opener_issues(game.flow.stages, game_nodes(game)):
        stage: Stage = game.flow.stages[index]
        if kind == "unknown":
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.opens_with_unknown",
                    message=f"The stage {stage.id} opens with the puzzle {stage.opens_with}, which does not exist.",
                    file=FLOW_FILE,
                    path=f"stages.{index}.opens_with",
                    fix_hint="Open the stage with the id of an existing puzzle from an earlier stage.",
                )
            )
        else:
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.opens_with_order",
                    message=f"The stage {stage.id} opens with {stage.opens_with}, but that puzzle is in the stage "
                    f"{puzzles[stage.opens_with].source.stage}, which is not an earlier stage.",
                    file=FLOW_FILE,
                    path=f"stages.{index}.opens_with",
                    fix_hint="Open each stage with a puzzle from an earlier stage, so players can open the envelope.",
                )
            )
    return findings


def reachable_parts(game: Game) -> tuple[set[str], set[str]]:
    """Return the stages that players can open and the puzzles that they can solve, from the start of the game."""
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    open_stages: set[str] = {game.flow.stages[0].id}
    solvable: set[str] = set()
    changed: bool = True
    while changed:
        changed = False
        for stage in game.flow.stages:
            if stage.id not in open_stages and stage.opens_with in solvable:
                open_stages.add(stage.id)
                changed = True
        for puzzle_id, puzzle in puzzles.items():
            known_dependencies: list[str] = [item for item in puzzle.source.depends_on if item in puzzles]
            if (
                puzzle_id not in solvable
                and puzzle.source.stage in open_stages
                and all(item in solvable for item in known_dependencies)
            ):
                solvable.add(puzzle_id)
                changed = True
    return open_stages, solvable


def reachability_findings(game: Game) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    open_stages, solvable = reachable_parts(game)
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        if puzzle.source.id in solvable or puzzle.source.stage not in positions:
            continue
        reason: str = (
            f"its stage {puzzle.source.stage} never opens"
            if puzzle.source.stage not in open_stages
            else "it depends on a puzzle that players can never solve"
        )
        findings.append(
            Finding(
                severity="error",
                rule="graph.unreachable",
                message=f"Players can never reach the puzzle {puzzle.source.id}: {reason}.",
                file=puzzle.file,
                path="depends_on",
                fix_hint="Fix the dependency or the stage opening that blocks it, so every puzzle can be reached.",
            )
        )
    return findings


def final_puzzle_findings(game: Game) -> list[Finding]:
    final_id: str | None = game.flow.final_puzzle
    issue: FinalPuzzleIssueKind | None = final_puzzle_issue(game.flow, game_nodes(game))
    if final_id is None:
        return []
    if issue == "unknown":
        return [
            Finding(
                severity="error",
                rule="graph.final_puzzle_unknown",
                message=f"The final puzzle {final_id} does not exist.",
                file=FLOW_FILE,
                path="final_puzzle",
                fix_hint="Set final_puzzle to the id of the puzzle that ends the game, or remove the field.",
            )
        ]
    final: AssembledPuzzle = puzzles_by_id(game)[final_id]
    findings: list[Finding] = []
    if issue == "stage":
        findings.append(
            Finding(
                severity="error",
                rule="graph.final_puzzle_stage",
                message=f"The final puzzle {final_id} is in the stage {final.source.stage}, not in the last stage "
                f"{game.flow.stages[-1].id}.",
                file=FLOW_FILE,
                path="final_puzzle",
                fix_hint="Move the final puzzle to the last stage, or name a puzzle of the last stage as final.",
            )
        )
    if game.flow.structure == "funnel":
        findings.extend(funnel_findings(game, final))
    findings.extend(feeder_variant_findings(game, final))
    return findings


def feeder_variant_findings(game: Game, final: AssembledPuzzle) -> list[Finding]:
    """Report an answer variant with other letters on a puzzle that the final puzzle uses.

    The final puzzle works on the letters or the digits of the earlier answers. A group that typed an accepted
    variant with other letters ("12" for "twelve") gets a wrong final answer, so only spellings that normalize to the
    same answer may count.
    """
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for feeder_id in final.source.depends_on:
        feeder: AssembledPuzzle | None = puzzles.get(feeder_id)
        if feeder is None:
            continue
        answer: str = normalize_answer(feeder.source.answer, game.config.language)
        others: list[str] = [
            variant for variant in feeder.source.accepted if normalize_answer(variant, game.config.language) != answer
        ]
        if not others:
            continue
        listed: str = ", ".join(f"'{variant}'" for variant in others)
        findings.append(
            Finding(
                severity="error",
                rule="graph.feeder_variant",
                message=f"{feeder_id} feeds the final puzzle {final.source.id}, but it also accepts {listed}: a group "
                "that types one of them uses other letters in the final puzzle.",
                file=feeder.file,
                path="accepted",
                fix_hint="Remove these variants. Make the answer format force one spelling instead (for example "
                "'a number in words'), or add the variant as a near miss whose message asks for the other form.",
            )
        )
    return findings


def funnel_findings(game: Game, final: AssembledPuzzle) -> list[Finding]:
    """In a funnel, every earlier stage feeds the final puzzle: it needs at least one puzzle of each one."""
    final_position: int | None = stage_positions(game).get(final.source.stage)
    if final_position is None:
        return []
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    needed_stages: set[str] = {
        puzzles[puzzle_id].source.stage for puzzle_id in transitive_dependencies(game_nodes(game))[final.source.id]
    }
    return [
        Finding(
            severity="error",
            rule="graph.funnel_missing_stage",
            message=f"The final puzzle {final.source.id} needs no puzzle of the stage {stage.id}, but the structure "
            "is a funnel.",
            file=final.file,
            path="depends_on",
            fix_hint=f"Add a puzzle of the stage {stage.id} to depends_on of {final.source.id}, directly or through "
            "another puzzle.",
        )
        for stage in game.flow.stages[:final_position]
        if stage.id not in needed_stages
    ]


def document_findings(game: Game) -> list[Finding]:
    stages_with_documents: set[str] = {document.meta.stage for document in game.documents}
    findings: list[Finding] = [
        Finding(
            severity="error",
            rule="graph.stage_without_documents",
            message=f"The stage {stage.id} has no document, so its envelope is empty.",
            file=FLOW_FILE,
            path=f"stages.{index}",
            fix_hint=f"Put at least one document in the stage {stage.id} (front matter `stage: {stage.id}`).",
        )
        for index, stage in enumerate(game.flow.stages)
        if stage.id not in stages_with_documents
    ]
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings.extend(
        Finding(
            severity="error",
            rule="graph.unknown_puzzle",
            message=f"The document {document.meta.id} belongs to the puzzle {document.meta.puzzle}, which does not "
            "exist.",
            file=document.file,
            path="puzzle",
            fix_hint=f"Use an existing puzzle id ({', '.join(puzzles)}), or remove the field.",
        )
        for document in game.documents
        if document.meta.puzzle is not None and document.meta.puzzle not in puzzles
    )
    return findings


def parallel_width_findings(game: Game) -> list[Finding]:
    first_stage: str = game.flow.stages[0].id
    in_first_stage: list[AssembledPuzzle] = [puzzle for puzzle in game.puzzles if puzzle.source.stage == first_stage]
    free: int = sum(1 for puzzle in in_first_stage if not puzzle.source.depends_on)
    wanted: int = min(game.brief.parallel_width, len(in_first_stage))
    if free >= wanted:
        return []
    return [
        Finding(
            severity="warning",
            rule="graph.parallel_width",
            message=f"The first stage offers {free} puzzles that players can start at once, but the group needs "
            f"{wanted} so that nobody waits.",
            file=FLOW_FILE,
            path="stages.0",
            fix_hint="Remove dependencies between the puzzles of the first stage, or add a free puzzle to it.",
        )
    ]


def artifact_findings(game: Game) -> list[Finding]:
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        if puzzle.artifact is None or not puzzle.artifact.html:
            continue
        mark: str = ARTIFACT_MARK.format(puzzle=puzzle.source.id)
        holders: list[str] = [document.meta.id for document in game.documents if mark in document.body_html]
        if not holders:
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.artifact_missing",
                    message=f"No document prints the material of the puzzle {puzzle.source.id}.",
                    file=puzzle.file,
                    fix_hint=f"Add `{{{{artifact}}}}` to the document whose front matter says `puzzle: "
                    f"{puzzle.source.id}`, or `{{{{artifact:{puzzle.source.id}}}}}` to another document.",
                )
            )
        elif len(holders) > 1:
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.artifact_duplicated",
                    message=f"The material of the puzzle {puzzle.source.id} is printed in {len(holders)} documents: "
                    f"{', '.join(holders)}.",
                    file=puzzle.file,
                    fix_hint="Keep the artifact reference in one document only.",
                )
            )
    return findings


def needed_text_findings(game: Game) -> list[Finding]:
    """Report a text that a puzzle's material needs but does not print, when no document of its stage prints it.

    The solver packet shows only the documents, so the panel cannot catch this: it sees the same gap as players.
    """
    positions: dict[str, int] = stage_positions(game)
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        if puzzle.artifact is None or not puzzle.artifact.needs_in_documents:
            continue
        limit: int = positions.get(puzzle.source.stage, len(positions))
        available: str = "\n".join(
            document.text for document in game.documents if positions.get(document.meta.stage, len(positions)) <= limit
        )
        missing: list[str] = [
            needed for needed in puzzle.artifact.needs_in_documents if not mentions(available, squash(needed))
        ]
        if not missing:
            continue
        listed: str = ", ".join(f"'{needed}'" for needed in missing)
        findings.append(
            Finding(
                severity="error",
                rule="graph.needed_text_missing",
                message=f"The material of {puzzle.source.id} needs {listed}, but no document that players have at "
                f"stage {puzzle.source.stage} prints it.",
                file=puzzle.file,
                fix_hint="Print these texts in a document of this puzzle, in the story world (for example a list of "
                "grid squares in a diary).",
            )
        )
    return findings


def unused_dependency_findings(game: Game, mechanics: Mapping[str, Mechanic]) -> list[Finding]:
    """Report a dependency whose answer the puzzle never uses: players then need nothing from the earlier puzzle.

    The answer must appear in the puzzle's parameters or in its own documents. A panel puzzle has no parameters to
    search, and a reader judges its use of earlier answers, so it is skipped.
    """
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        mechanic: Mechanic | None = mechanics.get(puzzle.source.mechanic)
        if not puzzle.source.depends_on or (mechanic is not None and mechanic.verification == "panel"):
            continue
        material: str = squash(" ".join(own_material_texts(game, puzzle)))
        for index, dependency_id in enumerate(puzzle.source.depends_on):
            dependency: AssembledPuzzle | None = puzzles.get(dependency_id)
            if dependency is None:
                continue
            forms: set[str] = {squash(dependency.source.answer), *dependency.accepted_normalized} - {""}
            if any(form in material for form in forms):
                continue
            findings.append(
                Finding(
                    severity="warning",
                    rule="graph.unused_dependency",
                    message=f"The puzzle {puzzle.source.id} depends on {dependency_id}, but the answer of "
                    f"{dependency_id} appears neither in its params nor in its documents, so players may not need it.",
                    file=puzzle.file,
                    path=f"depends_on.{index}",
                    fix_hint=f"Use the answer of {dependency_id} in the material of {puzzle.source.id} (as a key, a "
                    "number, or a word that players must combine), or remove the dependency.",
                )
            )
    return findings


def own_material_texts(game: Game, puzzle: AssembledPuzzle) -> list[str]:
    texts: list[str] = [json.dumps(puzzle.source.params, ensure_ascii=False)]
    texts.extend(document.text for document in game.documents if document.meta.puzzle == puzzle.source.id)
    if puzzle.artifact is not None:
        texts.append(puzzle.artifact.solver_text)
    return texts
