"""The puzzle graph: stages, dependencies, stage openings, reachability, the final puzzle, and artifact placement.

Players move through the game along this graph. A puzzle that depends on an unknown or a later puzzle, a stage that
never opens, or an artifact that no document prints makes the printed game impossible to finish.
"""

from mystery_forge.checks.game_index import FLOW_FILE, puzzles_by_id, stage_positions
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.spec.documents import ARTIFACT_MARK


def check_graph(game: Game) -> list[Finding]:
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
    ]


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
    positions: dict[str, int] = stage_positions(game)
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        for index, dependency_id in enumerate(puzzle.source.depends_on):
            dependency: AssembledPuzzle | None = puzzles.get(dependency_id)
            if dependency is None:
                findings.append(
                    Finding(
                        severity="error",
                        rule="graph.unknown_dependency",
                        message=f"The puzzle {puzzle.source.id} depends on {dependency_id}, which does not exist.",
                        file=puzzle.file,
                        path=f"depends_on.{index}",
                        fix_hint=f"Use an existing puzzle id: {', '.join(puzzles)}.",
                    )
                )
            elif positions.get(dependency.source.stage, -1) > positions.get(puzzle.source.stage, len(positions)):
                findings.append(
                    Finding(
                        severity="error",
                        rule="graph.dependency_later_stage",
                        message=f"The puzzle {puzzle.source.id} in stage {puzzle.source.stage} depends on "
                        f"{dependency_id} in the later stage {dependency.source.stage}.",
                        file=puzzle.file,
                        path=f"depends_on.{index}",
                        fix_hint="Depend only on puzzles of the same or an earlier stage, or move one of the puzzles.",
                    )
                )
    return findings


def transitive_dependencies(game: Game) -> dict[str, set[str]]:
    """Map each puzzle id to every puzzle that it needs, directly or through other puzzles. Unknown ids drop out."""
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    needed: dict[str, set[str]] = {}
    for puzzle_id, puzzle in puzzles.items():
        found: set[str] = set()
        pending: list[str] = list(puzzle.source.depends_on)
        while pending:
            dependency_id: str = pending.pop()
            if dependency_id in found or dependency_id not in puzzles:
                continue
            found.add(dependency_id)
            pending.extend(puzzles[dependency_id].source.depends_on)
        needed[puzzle_id] = found
    return needed


def dependency_loop_findings(game: Game) -> list[Finding]:
    needed: dict[str, set[str]] = transitive_dependencies(game)
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    in_loop: list[str] = sorted((puzzle_id for puzzle_id in needed if puzzle_id in needed[puzzle_id]), key=id_number)
    loops: list[list[str]] = []
    for puzzle_id in in_loop:
        loop: list[str] = [other for other in in_loop if other in needed[puzzle_id] and puzzle_id in needed[other]]
        if loop not in loops:
            loops.append(loop)
    return [
        Finding(
            severity="error",
            rule="graph.dependency_loop",
            message=f"The puzzles {', '.join(loop)} depend on each other in a loop, so players can never start them.",
            file=puzzles[loop[0]].file,
            path="depends_on",
            fix_hint="Remove one dependency of the loop. A puzzle can only depend on puzzles that players solve first.",
        )
        for loop in loops
    ]


def id_number(puzzle_id: str) -> int:
    return int(puzzle_id[1:])


def stage_opening_findings(game: Game) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for index, stage in enumerate(game.flow.stages[1:], start=1):
        opener: AssembledPuzzle | None = puzzles.get(stage.opens_with)
        if opener is None:
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
            continue
        opener_position: int | None = positions.get(opener.source.stage)
        if opener_position is not None and opener_position >= index:
            findings.append(
                Finding(
                    severity="error",
                    rule="graph.opens_with_order",
                    message=f"The stage {stage.id} opens with {stage.opens_with}, but that puzzle is in the stage "
                    f"{opener.source.stage}, which is not an earlier stage.",
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
    if final_id is None:
        return []
    final: AssembledPuzzle | None = puzzles_by_id(game).get(final_id)
    if final is None:
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
    findings: list[Finding] = []
    last_stage: str = game.flow.stages[-1].id
    if final.source.stage != last_stage:
        findings.append(
            Finding(
                severity="error",
                rule="graph.final_puzzle_stage",
                message=f"The final puzzle {final_id} is in the stage {final.source.stage}, not in the last stage "
                f"{last_stage}.",
                file=FLOW_FILE,
                path="final_puzzle",
                fix_hint="Move the final puzzle to the last stage, or name a puzzle of the last stage as final.",
            )
        )
    if game.flow.structure == "funnel":
        findings.extend(funnel_findings(game, final))
    return findings


def funnel_findings(game: Game, final: AssembledPuzzle) -> list[Finding]:
    """In a funnel, every earlier stage feeds the final puzzle: it needs at least one puzzle of each one."""
    final_position: int | None = stage_positions(game).get(final.source.stage)
    if final_position is None:
        return []
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    needed_stages: set[str] = {
        puzzles[puzzle_id].source.stage for puzzle_id in transitive_dependencies(game)[final.source.id]
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
