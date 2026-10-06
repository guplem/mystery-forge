"""The puzzle plan (`source/plan.yaml`) and its checks.

The planner decides the puzzles before anyone writes them: the mechanic, the stage, the answer, the dependencies, and
which documents each writer owns. Writers then work in parallel, so one document must have exactly one owner. The
checks here run on the plan alone, before the expensive writing starts, and catch the structural mistakes early.
"""

from collections import Counter
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path

from pydantic import Field

from mystery_forge.assemble import load_brief, load_config
from mystery_forge.brief import Brief
from mystery_forge.catalog.loader import mechanics_by_id
from mystery_forge.catalog.models import Mechanic
from mystery_forge.config import GameConfig
from mystery_forge.draw import mechanic_fits
from mystery_forge.findings import Finding
from mystery_forge.spec.loader import SOURCE_FOLDER, load_required_model
from mystery_forge.spec.models import (
    Difficulty,
    DocumentId,
    Flow,
    PuzzleId,
    RegistryId,
    ShortText,
    SourceModel,
    StageId,
    Story,
    Text,
)

PLAN_FILE: str = "plan.yaml"
MAX_LOOKUP_CIPHERS: int = 2
MAX_SAME_MECHANIC: int = 2
MIN_PLAYER_ACTIONS: int = 4
MINUTES_PER_STAGE: float = 5.0


class PlannedPuzzle(SourceModel):
    id: PuzzleId
    stage: StageId
    title: ShortText
    mechanic: RegistryId
    difficulty: Difficulty
    depends_on: list[PuzzleId] = Field(default_factory=list)
    answer: ShortText
    in_world_reason: Text
    reveals: Text
    # The documents that this puzzle's writer writes. The puzzle's material lives in one of them.
    documents: list[DocumentId] = Field(min_length=1)
    # Story documents that this puzzle reads. Their writer runs first, so the puzzle writer can quote them.
    relies_on: list[DocumentId] = Field(default_factory=list)
    notes: str = ""


class PlannedDocument(SourceModel):
    """A document that no puzzle owns: the case briefing, evidence for the deduction, red herrings."""

    id: DocumentId
    kind: RegistryId
    stage: StageId
    title: ShortText
    purpose: Text
    # Exact sentences that the document writer must include, such as a fact that a puzzle needs.
    must_contain: list[Text] = Field(default_factory=list)


class Plan(SourceModel):
    format_version: int = Field(ge=1, le=1)
    motif: Text
    puzzles: list[PlannedPuzzle] = Field(min_length=1)
    story_documents: list[PlannedDocument] = Field(default_factory=list)


def check_plan_folder(game_dir: Path, implemented_builders: frozenset[str]) -> list[Finding]:
    """Check `source/plan.yaml` against the story, the flow, the config, and the catalog."""
    findings: list[Finding] = []
    root: Path = game_dir / SOURCE_FOLDER
    plan: Plan | None = load_required_model(root, PLAN_FILE, Plan, findings)
    story: Story | None = load_required_model(root, "story.yaml", Story, findings)
    flow: Flow | None = load_required_model(root, "flow.yaml", Flow, findings)
    config: GameConfig | None = load_config(game_dir, findings)
    brief: Brief | None = load_brief(game_dir, findings)
    if plan is None or story is None or flow is None or config is None or brief is None:
        return findings
    checks: list[Callable[[], list[Finding]]] = [
        lambda: check_ids(plan),
        lambda: check_mechanics(plan, config, implemented_builders),
        lambda: check_graph(plan, flow),
        lambda: check_documents(plan, flow, story),
        lambda: check_variety(plan),
        lambda: check_budget(plan, config, brief),
    ]
    for run_check in checks:
        findings.extend(run_check())
    return findings


def plan_finding(rule: str, message: str, fix_hint: str, severity: str = "error") -> Finding:
    return Finding(
        severity="error" if severity == "error" else "warning",
        rule=rule,
        message=message,
        file=PLAN_FILE,
        fix_hint=fix_hint,
    )


def duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def check_ids(plan: Plan) -> list[Finding]:
    findings: list[Finding] = []
    for puzzle_id in duplicates([puzzle.id for puzzle in plan.puzzles]):
        findings.append(plan_finding("plan.duplicate_puzzle", f"Two puzzles use the id {puzzle_id}.", "Renumber one."))
    owned: list[str] = [document for puzzle in plan.puzzles for document in puzzle.documents]
    owned += [document.id for document in plan.story_documents]
    for document_id in duplicates(owned):
        findings.append(
            plan_finding(
                "plan.duplicate_document",
                f"The document {document_id} has two owners.",
                "Give every document exactly one owner: one puzzle, or the story documents.",
            )
        )
    return findings


def check_mechanics(plan: Plan, config: GameConfig, implemented_builders: frozenset[str]) -> list[Finding]:
    catalog: dict[str, Mechanic] = mechanics_by_id()
    findings: list[Finding] = []
    for puzzle in plan.puzzles:
        mechanic: Mechanic | None = catalog.get(puzzle.mechanic)
        if mechanic is None:
            findings.append(
                plan_finding(
                    "plan.mechanic_unknown",
                    f"{puzzle.id}: the mechanic '{puzzle.mechanic}' is not in the catalog.",
                    "Pick a mechanic from `forge catalog list --implemented`.",
                )
            )
        elif mechanic.verification != "panel" and mechanic.builder not in implemented_builders:
            findings.append(
                plan_finding(
                    "plan.mechanic_unavailable",
                    f"{puzzle.id}: no code builds '{puzzle.mechanic}' yet.",
                    "Pick a mechanic from `forge catalog list --implemented`.",
                )
            )
        elif not mechanic_fits(mechanic, config, implemented_builders, puzzle.difficulty):
            findings.append(
                plan_finding(
                    "plan.mechanic_unfit",
                    f"{puzzle.id}: '{puzzle.mechanic}' does not fit the config (equipment, audience, "
                    f"difficulty {puzzle.difficulty}, or an avoided puzzle kind).",
                    "Pick another candidate from source/draw.json, or change the puzzle's difficulty.",
                )
            )
    return findings


def check_graph(plan: Plan, flow: Flow) -> list[Finding]:
    findings: list[Finding] = []
    stage_order: dict[str, int] = {stage.id: index for index, stage in enumerate(flow.stages)}
    puzzles: dict[str, PlannedPuzzle] = {puzzle.id: puzzle for puzzle in plan.puzzles}
    for puzzle in plan.puzzles:
        if puzzle.stage not in stage_order:
            findings.append(
                plan_finding(
                    "plan.stage_unknown",
                    f"{puzzle.id}: stage {puzzle.stage} is not in flow.yaml.",
                    "Use a stage id from flow.yaml, or add the stage.",
                )
            )
            continue
        for dependency in puzzle.depends_on:
            if dependency not in puzzles:
                findings.append(
                    plan_finding(
                        "plan.dependency_unknown",
                        f"{puzzle.id} depends on {dependency}, which is not planned.",
                        "Remove the dependency or plan the puzzle.",
                    )
                )
            elif stage_order.get(puzzles[dependency].stage, 99) > stage_order[puzzle.stage]:
                findings.append(
                    plan_finding(
                        "plan.dependency_later_stage",
                        f"{puzzle.id} depends on {dependency}, which sits in a later stage.",
                        "A puzzle can only need answers from its own stage or earlier stages.",
                    )
                )
    if has_cycle(puzzles):
        findings.append(
            plan_finding(
                "plan.dependency_cycle",
                "The puzzle dependencies form a cycle.",
                "Remove a dependency so that some puzzle in the loop can be solved first.",
            )
        )
    findings.extend(check_stage_openers(flow, puzzles, stage_order))
    final: str | None = flow.final_puzzle
    if final is not None and (final not in puzzles or puzzles[final].stage != flow.stages[-1].id):
        findings.append(
            plan_finding(
                "plan.final_puzzle",
                f"The final puzzle {final} must be a planned puzzle of the last stage.",
                "Point final_puzzle in flow.yaml at a puzzle of the last stage.",
            )
        )
    return findings


def check_stage_openers(flow: Flow, puzzles: dict[str, PlannedPuzzle], stage_order: dict[str, int]) -> list[Finding]:
    findings: list[Finding] = []
    for index, stage in enumerate(flow.stages[1:], start=1):
        opener: PlannedPuzzle | None = puzzles.get(stage.opens_with)
        if opener is None or stage_order.get(opener.stage, 99) >= index:
            findings.append(
                plan_finding(
                    "plan.stage_opener",
                    f"Stage {stage.id} must open with a planned puzzle of an earlier stage, not {stage.opens_with}.",
                    "Set opens_with to a puzzle of an earlier stage.",
                )
            )
    return findings


def has_cycle(puzzles: dict[str, PlannedPuzzle]) -> bool:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(puzzle_id: str) -> bool:
        if puzzle_id in done or puzzle_id not in puzzles:
            return False
        if puzzle_id in visiting:
            return True
        visiting.add(puzzle_id)
        found: bool = any(visit(dependency) for dependency in puzzles[puzzle_id].depends_on)
        visiting.discard(puzzle_id)
        done.add(puzzle_id)
        return found

    return any(visit(puzzle_id) for puzzle_id in puzzles)


def check_documents(plan: Plan, flow: Flow, story: Story) -> list[Finding]:
    findings: list[Finding] = []
    stage_order: dict[str, int] = {stage.id: index for index, stage in enumerate(flow.stages)}
    story_documents: dict[str, PlannedDocument] = {document.id: document for document in plan.story_documents}
    document_stages: dict[str, str] = {document.id: document.stage for document in plan.story_documents}
    for puzzle in plan.puzzles:
        for document_id in puzzle.documents:
            document_stages.setdefault(document_id, puzzle.stage)
    for stage in flow.stages:
        if stage.id not in document_stages.values():
            findings.append(
                plan_finding(
                    "plan.stage_empty",
                    f"Stage {stage.id} has no document.",
                    "Plan at least one document in every stage.",
                )
            )
    for clue in story.clues:
        if clue.document not in document_stages:
            findings.append(
                plan_finding(
                    "plan.clue_document",
                    f"The story clue '{clue.id}' lives in {clue.document}, which the plan does not include.",
                    "Add that document to story_documents (with the quote in must_contain).",
                )
            )
    for puzzle in plan.puzzles:
        for document_id in puzzle.relies_on:
            document: PlannedDocument | None = story_documents.get(document_id)
            if document is None or stage_order.get(document.stage, 99) > stage_order.get(puzzle.stage, 0):
                findings.append(
                    plan_finding(
                        "plan.relies_on",
                        f"{puzzle.id} relies on {document_id}, which must be a story document of its stage or earlier.",
                        "List only story documents that players already have when they reach this puzzle.",
                    )
                )
    return findings


def check_variety(plan: Plan) -> list[Finding]:
    catalog: dict[str, Mechanic] = mechanics_by_id()
    known: list[PlannedPuzzle] = [puzzle for puzzle in plan.puzzles if puzzle.mechanic in catalog]
    findings: list[Finding] = []
    lookup_ciphers: int = sum(1 for puzzle in known if catalog[puzzle.mechanic].lookup_cipher)
    if lookup_ciphers > MAX_LOOKUP_CIPHERS:
        findings.append(
            plan_finding(
                "plan.lookup_ciphers",
                f"The plan has {lookup_ciphers} lookup ciphers; the most is 2.",
                "Replace a cipher with a puzzle of another player action.",
            )
        )
    for mechanic_id in sorted(set(duplicates([puzzle.mechanic for puzzle in known]))):
        if sum(1 for puzzle in known if puzzle.mechanic == mechanic_id) > MAX_SAME_MECHANIC:
            findings.append(
                plan_finding(
                    "plan.same_mechanic",
                    f"More than 2 puzzles use '{mechanic_id}'.",
                    "Swap one for another candidate.",
                    "warning",
                )
            )
    actions: list[str] = [catalog[puzzle.mechanic].player_action for puzzle in known]
    if len(set(actions)) < min(MIN_PLAYER_ACTIONS, len(known)):
        findings.append(
            plan_finding(
                "plan.few_actions",
                f"The puzzles use only {len(set(actions))} player actions.",
                "Mix decoding, searching, logic, wordplay, arithmetic, spatial, and deduction.",
                "warning",
            )
        )
    if any(first == second for first, second in pairwise(actions)):
        findings.append(
            plan_finding(
                "plan.same_action_in_a_row",
                "Two puzzles in a row ask players to do the same thing.",
                "Reorder the puzzles or change one mechanic.",
                "warning",
            )
        )
    return findings


def plan_minutes(puzzle_minutes: list[float], brief: Brief, audience: str) -> float:
    """Estimate the playing time: catalog minutes, faster for bigger groups, slower solo and for kids."""
    speedup: float = 1 + 0.6 * (brief.parallel_width - 1)
    solo_factor: float = 1.25 if brief.players == 1 else 1.0
    kids_factor: float = 1.4 if audience == "kids" else 1.0
    return sum(puzzle_minutes) / speedup * solo_factor * kids_factor + MINUTES_PER_STAGE * brief.stage_count


def check_budget(plan: Plan, config: GameConfig, brief: Brief) -> list[Finding]:
    catalog: dict[str, Mechanic] = mechanics_by_id()
    findings: list[Finding] = []
    if abs(len(plan.puzzles) - brief.puzzle_count) > 2:
        findings.append(
            plan_finding(
                "plan.puzzle_count",
                f"The plan has {len(plan.puzzles)} puzzles; the brief asks for {brief.puzzle_count}.",
                "Add or remove puzzles to match brief.json.",
                "warning",
            )
        )
    minutes: list[float] = [
        float(getattr(catalog[puzzle.mechanic].minutes, puzzle.difficulty))
        for puzzle in plan.puzzles
        if puzzle.mechanic in catalog
    ]
    estimate: float = plan_minutes(minutes, brief, config.audience)
    target: int = config.duration_minutes
    ratio: float = estimate / target
    if not 0.75 <= ratio <= 1.25:
        severity: str = "error" if not 0.5 <= ratio <= 1.5 else "warning"
        findings.append(
            plan_finding(
                "plan.budget",
                f"The plan takes about {round(estimate)} minutes; the game should take {target}.",
                "Change the puzzle count or difficulties. Catalog minutes per mechanic: `forge catalog show <id>`.",
                severity,
            )
        )
    return findings
