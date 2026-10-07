"""The puzzle plan (`source/plan.yaml`) and its checks.

The planner decides the puzzles before anyone writes them: the mechanic, the stage, the answer, the dependencies, and
which documents each writer owns. Writers then work in parallel, so one document must have exactly one owner. The
checks here run on the plan alone, before the expensive writing starts, and catch the structural mistakes early.
The graph, variety, and budget rules call the same pure functions as the whole-game checks in `checks/`, so a plan
that passes does not fail the same rule later. Two checks run later, on the written game, because writers and fixers
can drift from the plan: a `must_contain` sentence that the documents lost, and a puzzle named by its old plan title.
"""

from collections.abc import Callable
from pathlib import Path

from pydantic import Field

from mystery_forge.assemble import load_brief, load_config
from mystery_forge.brief import Brief
from mystery_forge.catalog.loader import mechanics_by_id
from mystery_forge.catalog.models import Mechanic
from mystery_forge.checks.budget import (
    difficulty_drift,
    duration_severity,
    estimate_play_minutes,
    required_difficulty,
)
from mystery_forge.checks.game_index import code_order_key
from mystery_forge.checks.graph import (
    PuzzleNode,
    dependency_issues,
    dependency_loops,
    final_puzzle_issue,
    stage_opener_issues,
)
from mystery_forge.checks.ledger import normalize_quote_text
from mystery_forge.checks.variety import (
    MechanicUse,
    lookup_cipher_ids,
    missing_player_actions,
    overused_mechanics,
    same_action_pairs,
)
from mystery_forge.config import GameConfig
from mystery_forge.draw import mechanic_fits
from mystery_forge.findings import Finding, Severity
from mystery_forge.game import Game
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
    find_duplicates,
)

PLAN_FILE: str = "plan.yaml"
# A shorter title, such as "The tide", also occurs in plain sentences, so a search for it finds false matches.
MIN_STALE_TITLE_LENGTH: int = 12


class PlannedPuzzle(SourceModel):
    id: PuzzleId
    stage: StageId
    title: ShortText
    mechanic: RegistryId
    difficulty: Difficulty
    depends_on: list[PuzzleId] = Field(default_factory=list)
    answer: ShortText
    in_world_reason: Text
    # Who the hiding defeats in the story, such as "the crew". A hiding that defeats nobody has no reason to exist.
    hidden_from: Text
    reveals: Text
    # The documents that this puzzle's writer writes. The puzzle's material lives in one of them.
    documents: list[DocumentId] = Field(min_length=1)
    # Story documents that this puzzle reads. Their writer runs first, so the puzzle writer can quote them.
    relies_on: list[DocumentId] = Field(default_factory=list)
    # Exact sentences that this puzzle's documents must include, such as the marker that the final puzzle points to.
    must_contain: list[Text] = Field(default_factory=list)
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
        lambda: check_jobs(plan, flow, story),
        lambda: check_documents(plan, flow, story),
        lambda: check_variety(plan, flow),
        lambda: check_budget(plan, config, brief),
    ]
    for run_check in checks:
        findings.extend(run_check())
    return findings


def planned_sentence_findings(game_dir: Path, game: Game) -> list[Finding]:
    """Report each `must_contain` sentence of the plan that its written documents lost.

    Writers and fixers change the documents after the plan. A lost sentence silently breaks the puzzle or the proof
    that needs it, such as the marker that the final puzzle points to. A missing or broken plan, and a planned
    document that nobody wrote, are the plan check's and the loader's findings, not these.
    """
    plan: Plan | None = load_required_model(game_dir / SOURCE_FOLDER, PLAN_FILE, Plan, [])
    if plan is None:
        return []
    texts: dict[str, str] = {document.meta.id: normalize_quote_text(document.text) for document in game.documents}
    owners: list[tuple[str, list[str], list[str]]] = [
        (f"puzzle {puzzle.id}", puzzle.documents, puzzle.must_contain) for puzzle in plan.puzzles
    ]
    owners += [
        (f"story document {document.id}", [document.id], document.must_contain) for document in plan.story_documents
    ]
    findings: list[Finding] = []
    for owner, document_ids, sentences in owners:
        written: list[str] = [document_id for document_id in document_ids if document_id in texts]
        if not written:
            continue
        findings.extend(
            Finding(
                severity="error",
                rule="plan.must_contain_missing",
                message=f'The plan says that the documents of {owner} contain "{sentence}", but none does.',
                file=f"documents/{written[0]}.md",
                fix_hint="Put the sentence back word for word: another puzzle or the deduction needs it. Only a fix "
                "that may change plan.yaml may change the sentence, and it changes it in both places.",
            )
            for sentence in sentences
            if not any(normalize_quote_text(sentence) in texts[document_id] for document_id in written)
        )
    return findings


def stale_title_findings(game_dir: Path, game: Game) -> list[Finding]:
    """Report a puzzle that a hint, a solution, or a document names by its old plan title.

    Writers name the other puzzles by title, and they read the titles in the plan. A writer may later rename its own
    puzzle, and then the old name reaches the printed solutions, where players look for a puzzle that does not exist.
    """
    plan: Plan | None = load_required_model(game_dir / SOURCE_FOLDER, PLAN_FILE, Plan, [])
    if plan is None:
        return []
    titles: dict[str, str] = {puzzle.source.id: puzzle.source.title for puzzle in game.puzzles}
    renamed: list[tuple[str, str]] = [
        (planned.title, titles[planned.id])
        for planned in plan.puzzles
        if planned.id in titles
        and planned.title.casefold() != titles[planned.id].casefold()
        and len(planned.title) >= MIN_STALE_TITLE_LENGTH
    ]
    texts: list[tuple[str, str]] = [
        (
            puzzle.file,
            " ".join([*(step.text for step in puzzle.source.solution), *(hint.text for hint in puzzle.source.hints)]),
        )
        for puzzle in game.puzzles
    ]
    texts += [(document.file, document.text) for document in game.documents]
    return [
        Finding(
            severity="error",
            rule="plan.stale_title",
            message=f'{file} names a puzzle "{old}", its title in the plan. The puzzle is now called "{new}".',
            file=file,
            fix_hint=f'Write "{new}" instead, or the printed code of the puzzle.',
        )
        for file, text in texts
        for old, new in renamed
        if old.casefold() in text.casefold()
    ]


def plan_finding(rule: str, message: str, fix_hint: str, severity: Severity = "error") -> Finding:
    return Finding(severity=severity, rule=rule, message=message, file=PLAN_FILE, fix_hint=fix_hint)


def plan_nodes(plan: Plan) -> list[PuzzleNode]:
    return [
        PuzzleNode(id=puzzle.id, stage=puzzle.stage, depends_on=tuple(puzzle.depends_on)) for puzzle in plan.puzzles
    ]


def check_ids(plan: Plan) -> list[Finding]:
    findings: list[Finding] = []
    for puzzle_id in find_duplicates([puzzle.id for puzzle in plan.puzzles]):
        findings.append(plan_finding("plan.duplicate_puzzle", f"Two puzzles use the id {puzzle_id}.", "Renumber one."))
    owned: list[str] = [document for puzzle in plan.puzzles for document in puzzle.documents]
    owned += [document.id for document in plan.story_documents]
    for document_id in find_duplicates(owned):
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
    stage_ids: list[str] = [stage.id for stage in flow.stages]
    nodes: list[PuzzleNode] = plan_nodes(plan)
    findings: list[Finding] = [
        plan_finding(
            "plan.stage_unknown",
            f"{puzzle.id}: stage {puzzle.stage} is not in flow.yaml.",
            "Use a stage id from flow.yaml, or add the stage.",
        )
        for puzzle in plan.puzzles
        if puzzle.stage not in stage_ids
    ]
    for issue in dependency_issues(nodes, stage_ids):
        if issue.kind == "unknown":
            findings.append(
                plan_finding(
                    "plan.dependency_unknown",
                    f"{issue.puzzle_id} depends on {issue.dependency_id}, which is not planned.",
                    "Remove the dependency or plan the puzzle.",
                )
            )
        else:
            findings.append(
                plan_finding(
                    "plan.dependency_later_stage",
                    f"{issue.puzzle_id} depends on {issue.dependency_id}, which sits in a later stage.",
                    "A puzzle can only need answers from its own stage or earlier stages.",
                )
            )
    findings.extend(
        plan_finding(
            "plan.dependency_cycle",
            f"The puzzles {', '.join(loop)} depend on each other in a cycle.",
            "Remove a dependency so that some puzzle in the loop can be solved first.",
        )
        for loop in dependency_loops(nodes)
    )
    findings.extend(
        plan_finding(
            "plan.stage_opener",
            f"Stage {flow.stages[index].id} must open with a planned puzzle of an earlier stage, not "
            f"{flow.stages[index].opens_with}.",
            "Set opens_with to a puzzle of an earlier stage.",
        )
        for index, _ in stage_opener_issues(flow.stages, nodes)
    )
    if final_puzzle_issue(flow, nodes) is not None:
        findings.append(
            plan_finding(
                "plan.final_puzzle",
                f"The final puzzle {flow.final_puzzle} must be a planned puzzle of the last stage.",
                "Point final_puzzle in flow.yaml at a puzzle of the last stage.",
            )
        )
    return findings


def check_jobs(plan: Plan, flow: Flow, story: Story) -> list[Finding]:
    """Every hidden story clue needs a planned puzzle that reveals it, and every puzzle needs a job."""
    planned: set[str] = {puzzle.id for puzzle in plan.puzzles}
    revealers: set[str] = {clue.revealed_by or "" for clue in story.clues if clue.hidden}
    findings: list[Finding] = [
        plan_finding(
            "plan.hidden_clue_unplanned",
            f"The hidden story clue '{clue.id}' is revealed by {clue.revealed_by or 'no puzzle'}, which is not a "
            "planned puzzle.",
            "Set revealed_by of the clue in story.yaml to the planned puzzle whose answer reveals the fact.",
        )
        for clue in story.clues
        if clue.hidden and clue.revealed_by not in planned
    ]
    needed: set[str] = {dependency for puzzle in plan.puzzles for dependency in puzzle.depends_on}
    openers: set[str] = {stage.opens_with for stage in flow.stages}
    findings.extend(
        plan_finding(
            "plan.dead_end",
            f"{puzzle.id} has no job: no puzzle depends on it, no stage opens with it, it is not the final "
            "puzzle, and it reveals no hidden clue.",
            "Give the puzzle a job: let it open a stage, feed the final puzzle, or reveal a hidden clue of "
            "story.yaml (revealed_by). Otherwise remove it.",
        )
        for puzzle in plan.puzzles
        if puzzle.id not in needed | openers | revealers | {flow.final_puzzle or ""}
    )
    return findings


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
        if clue.document is not None and clue.document not in document_stages:
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


def check_variety(plan: Plan, flow: Flow) -> list[Finding]:
    catalog: dict[str, Mechanic] = mechanics_by_id()
    positions: dict[str, int] = {stage.id: index for index, stage in enumerate(flow.stages)}
    ordered: list[PlannedPuzzle] = sorted(
        plan.puzzles, key=lambda puzzle: code_order_key(positions, puzzle.stage, puzzle.id)
    )
    uses: list[MechanicUse] = [
        (puzzle.id, catalog[puzzle.mechanic]) for puzzle in ordered if puzzle.mechanic in catalog
    ]
    findings: list[Finding] = []
    lookups: list[str] = lookup_cipher_ids(uses)
    if lookups:
        findings.append(
            plan_finding(
                "plan.lookup_ciphers",
                f"The plan has {len(lookups)} lookup ciphers ({', '.join(lookups)}); the most is 2.",
                "Replace a cipher with a puzzle of another player action.",
            )
        )
    findings.extend(
        plan_finding(
            "plan.same_mechanic",
            f"{count} puzzles use '{mechanic_id}'; the most is 2.",
            "Swap one for another candidate.",
            "warning",
        )
        for mechanic_id, count in overused_mechanics(uses).items()
    )
    wanted: int | None = missing_player_actions(uses, len(plan.puzzles))
    if wanted is not None:
        findings.append(
            plan_finding(
                "plan.few_actions",
                f"The puzzles use only {len({mechanic.player_action for _, mechanic in uses})} player actions; the "
                f"plan needs {wanted}.",
                "Mix decoding, searching, logic, wordplay, arithmetic, spatial, and deduction.",
                "warning",
            )
        )
    findings.extend(
        plan_finding(
            "plan.same_action_in_a_row",
            f"{puzzle_id} asks players to do the same thing as {previous_id}, the puzzle before it in code order.",
            "Reorder the puzzles or change one mechanic.",
            "warning",
        )
        for previous_id, puzzle_id in same_action_pairs(uses)
    )
    return findings


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
    # The documents do not exist yet, so the estimate reads the whole reading budget of the brief.
    estimate: float = estimate_play_minutes(
        puzzle_minutes=[
            catalog[puzzle.mechanic].minutes.for_level(puzzle.difficulty)
            for puzzle in plan.puzzles
            if puzzle.mechanic in catalog
        ],
        players=brief.players,
        parallel_width=brief.parallel_width,
        audience=config.audience,
        stage_count=brief.stage_count,
        reading_words=brief.reading_words,
    )
    if difficulty_drift([puzzle.difficulty for puzzle in plan.puzzles], config.difficulty):
        findings.append(
            plan_finding(
                "plan.difficulty_drift",
                f"Fewer than half of the planned puzzles are {required_difficulty(config.difficulty)} or harder, but "
                f"the game is {config.difficulty}.",
                "Raise difficulties, or pick mechanics whose range reaches it (`forge catalog show <id>`). Never "
                "lower a puzzle's difficulty to fit a mechanic.",
            )
        )
    target: int = config.duration_minutes
    severity: Severity | None = duration_severity(estimate, target)
    if severity is not None:
        findings.append(
            plan_finding(
                "plan.budget",
                f"The plan takes about {round(estimate)} minutes; the game should take {target}.",
                "Change the puzzle count or difficulties. Catalog minutes per mechanic: `forge catalog show <id>`.",
                severity,
            )
        )
    return findings
