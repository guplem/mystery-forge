from test_checks_support import (
    edit_assembled_puzzle,
    edit_document,
    edit_flow,
    edit_puzzle,
    golden_game,
    golden_mechanics,
    only_rule,
    rules,
)

from mystery_forge.checks.graph import (
    PuzzleNode,
    check_graph,
    dependency_issues,
    dependency_loops,
    final_puzzle_issue,
    stage_opener_issues,
)
from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.mechanics.base import Artifact
from mystery_forge.spec.models import Stage


def graph_findings(game: Game) -> list[Finding]:
    return check_graph(game, golden_mechanics())


def structure_findings(game: Game) -> list[Finding]:
    """The graph findings without graph.unused_dependency, for edits that add a dependency the material ignores."""
    return [finding for finding in graph_findings(game) if finding.rule != "graph.unused_dependency"]


def test_the_golden_graph_has_no_findings() -> None:
    assert graph_findings(golden_game()) == []


def test_a_puzzle_or_document_in_an_unknown_stage_is_an_error() -> None:
    game: Game = edit_puzzle(golden_game(), "P2", stage="F")
    game = edit_document(game, "D5", meta={"stage": "G"})
    findings = only_rule(graph_findings(game), "graph.unknown_stage")
    assert [(finding.file, finding.path) for finding in findings] == [
        ("puzzles/P2.yaml", "stage"),
        ("documents/D5.md", "stage"),
    ]
    assert all(finding.severity == "error" and finding.fix_hint for finding in findings)


def test_an_unknown_dependency_is_an_error_and_does_not_block_reachability() -> None:
    findings = graph_findings(edit_puzzle(golden_game(), "P3", depends_on=["P1", "P9"]))
    assert rules(findings) == ["graph.unknown_dependency"]
    assert findings[0].path == "depends_on.1"
    assert "P9" in findings[0].message


def test_a_dependency_in_a_later_stage_is_an_error() -> None:
    findings = structure_findings(edit_puzzle(golden_game(), "P2", depends_on=["P3"]))
    assert rules(findings) == ["graph.dependency_later_stage"]
    assert findings[0].file == "puzzles/P2.yaml"
    assert findings[0].path == "depends_on.0"


def test_a_dependency_loop_is_one_error_per_loop() -> None:
    game: Game = edit_puzzle(golden_game(), "P1", depends_on=["P2"])
    game = edit_puzzle(game, "P2", depends_on=["P1"])
    findings = graph_findings(game)
    loops = only_rule(findings, "graph.dependency_loop")
    assert len(loops) == 1
    assert loops[0].file == "puzzles/P1.yaml"
    assert "P1, P2" in loops[0].message
    assert len(only_rule(findings, "graph.unreachable")) == 3


def test_a_puzzle_that_depends_on_itself_is_a_loop() -> None:
    findings = only_rule(graph_findings(edit_puzzle(golden_game(), "P2", depends_on=["P2"])), "graph.dependency_loop")
    assert [finding.file for finding in findings] == ["puzzles/P2.yaml"]


def test_a_stage_that_opens_with_an_unknown_or_later_puzzle_is_an_error() -> None:
    stages: list[Stage] = list(golden_game().flow.stages)
    unknown: Game = edit_flow(golden_game(), stages=[stages[0], stages[1].model_copy(update={"opens_with": "P7"})])
    findings = graph_findings(unknown)
    assert rules(findings)[0] == "graph.opens_with_unknown"
    assert findings[0].file == "flow.yaml"
    assert findings[0].path == "stages.1.opens_with"
    same_stage: Game = edit_flow(golden_game(), stages=[stages[0], stages[1].model_copy(update={"opens_with": "P3"})])
    assert "graph.opens_with_order" in rules(graph_findings(same_stage))


def test_an_opening_puzzle_in_an_unknown_stage_is_reported_only_once() -> None:
    findings = graph_findings(edit_puzzle(golden_game(), "P1", stage="F"))
    assert "graph.opens_with_order" not in rules(findings)
    assert "graph.unknown_stage" in rules(findings)


def test_a_puzzle_in_a_stage_that_never_opens_is_unreachable() -> None:
    stages: list[Stage] = list(golden_game().flow.stages)
    game: Game = edit_flow(golden_game(), stages=[stages[0], stages[1].model_copy(update={"opens_with": "P3"})])
    unreachable = only_rule(graph_findings(game), "graph.unreachable")
    assert [finding.file for finding in unreachable] == ["puzzles/P3.yaml"]
    assert "never opens" in unreachable[0].message


def test_the_final_puzzle_must_exist_and_sit_in_the_last_stage() -> None:
    unknown = graph_findings(edit_flow(golden_game(), final_puzzle="P8"))
    assert rules(unknown) == ["graph.final_puzzle_unknown"]
    assert unknown[0].path == "final_puzzle"
    early = graph_findings(edit_flow(golden_game(), final_puzzle="P2"))
    assert rules(early) == ["graph.final_puzzle_stage"]
    assert graph_findings(edit_flow(golden_game(), final_puzzle=None)) == []


def test_a_puzzle_that_feeds_the_final_puzzle_accepts_only_the_same_letters() -> None:
    same_letters = edit_puzzle(golden_game(), "P1", accepted=["The Boathouse", "boat-house"])
    assert graph_findings(same_letters) == []
    other_letters = edit_puzzle(golden_game(), "P1", accepted=["the boathouse", "boat shed", "the shed"])
    findings = only_rule(graph_findings(other_letters), "graph.feeder_variant")
    assert [(finding.file, finding.path, finding.severity) for finding in findings] == [
        ("puzzles/P1.yaml", "accepted", "error")
    ]
    assert "'boat shed', 'the shed'" in findings[0].message
    assert "P3" in findings[0].message
    not_a_feeder = edit_puzzle(golden_game(), "P2", accepted=["726"])
    assert only_rule(graph_findings(not_a_feeder), "graph.feeder_variant") == []
    assert only_rule(graph_findings(edit_flow(other_letters, final_puzzle=None)), "graph.feeder_variant") == []


def test_a_funnel_final_puzzle_must_depend_on_every_earlier_stage() -> None:
    funnel: Game = edit_flow(golden_game(), structure="funnel")
    assert graph_findings(funnel) == []
    missing = graph_findings(edit_puzzle(funnel, "P3", depends_on=[]))
    assert rules(missing) == ["graph.funnel_missing_stage"]
    assert "A" in missing[0].message
    in_unknown_stage = graph_findings(edit_puzzle(funnel, "P3", stage="F"))
    assert "graph.funnel_missing_stage" not in rules(in_unknown_stage)


def test_a_funnel_counts_transitive_dependencies() -> None:
    stages: list[Stage] = list(golden_game().flow.stages)
    stage_c = Stage(id="C", label="The tower", opens_with="P3")
    game: Game = edit_flow(golden_game(), structure="funnel", stages=[*stages, stage_c], final_puzzle="P2")
    game = edit_puzzle(game, "P2", stage="C", depends_on=["P3"])
    # P3 feeds the final puzzle now, so it may not accept "at low tide".
    game = edit_puzzle(game, "P3", accepted=[])
    game = edit_document(game, "D3", meta={"stage": "C"})
    assert structure_findings(game) == []


def test_a_stage_without_documents_and_an_unknown_document_puzzle_are_errors() -> None:
    game: Game = edit_document(golden_game(), "D4", meta={"stage": "A", "puzzle": None})
    game = edit_document(game, "D5", meta={"stage": "A", "puzzle": "P6"})
    findings = graph_findings(game)
    assert rules(findings) == ["graph.stage_without_documents", "graph.unknown_puzzle"]
    assert findings[0].path == "stages.1"
    assert (findings[1].file, findings[1].path) == ("documents/D5.md", "puzzle")


def test_too_few_free_puzzles_in_the_first_stage_is_a_warning() -> None:
    wide: Game = golden_game().model_copy(
        update={"brief": golden_game().brief.model_copy(update={"parallel_width": 2})}
    )
    assert graph_findings(wide) == []
    findings = structure_findings(edit_puzzle(wide, "P2", depends_on=["P1"]))
    assert rules(findings) == ["graph.parallel_width"]
    assert findings[0].severity == "warning"


def test_a_built_artifact_must_sit_in_exactly_one_document() -> None:
    missing = graph_findings(edit_document(golden_game(), "D2", body_html="<p>no mark</p>"))
    assert rules(missing) == ["graph.artifact_missing"]
    assert missing[0].file == "puzzles/P1.yaml"
    twice: Game = edit_document(golden_game(), "D5", body_html="<p>⟦artifact:P1⟧</p>")
    duplicated = graph_findings(twice)
    assert rules(duplicated) == ["graph.artifact_duplicated"]
    assert "D2, D5" in duplicated[0].message


def test_an_empty_or_missing_artifact_needs_no_document() -> None:
    no_html: Game = edit_assembled_puzzle(golden_game(), "P1", artifact=Artifact(html="", solver_text=""))
    assert graph_findings(edit_document(no_html, "D2", body_html="")) == []
    no_artifact: Game = edit_assembled_puzzle(golden_game(), "P1", artifact=None)
    assert graph_findings(edit_document(no_artifact, "D2", body_html="")) == []


def test_a_dependency_whose_answer_the_puzzle_never_uses_is_a_warning() -> None:
    built: Game = edit_puzzle(golden_game(), "P3", mechanic="caesar-cipher")
    findings = graph_findings(built)
    assert rules(findings) == ["graph.unused_dependency"]
    assert (findings[0].file, findings[0].path, findings[0].severity) == ("puzzles/P3.yaml", "depends_on.0", "warning")
    assert "P1" in findings[0].message
    assert graph_findings(edit_puzzle(built, "P3", params={"key": "Boat-House"})) == []
    in_document: Game = edit_document(built, "D4", text="The key word is BOATHOUSE.")
    assert graph_findings(in_document) == []
    in_artifact: Game = edit_assembled_puzzle(built, "P3", artifact=Artifact(html="<p></p>", solver_text="boathouse"))
    assert only_rule(graph_findings(in_artifact), "graph.unused_dependency") == []
    no_artifact: Game = edit_assembled_puzzle(built, "P3", artifact=None)
    assert rules(graph_findings(no_artifact)) == ["graph.unused_dependency"]


def test_a_panel_puzzle_or_an_unknown_dependency_skips_the_unused_dependency_check() -> None:
    assert graph_findings(golden_game()) == []
    unknown: Game = edit_puzzle(golden_game(), "P3", mechanic="caesar-cipher", depends_on=["P9"])
    assert only_rule(graph_findings(unknown), "graph.unused_dependency") == []


def nodes(*specs: tuple[str, str, tuple[str, ...]]) -> list[PuzzleNode]:
    return [PuzzleNode(id=puzzle_id, stage=stage, depends_on=depends_on) for puzzle_id, stage, depends_on in specs]


def test_the_shared_graph_rules_work_on_plain_puzzle_data() -> None:
    graph = nodes(("P1", "A", ("P2",)), ("P2", "A", ("P1", "P9")), ("P3", "B", ()), ("P4", "A", ("P3",)))
    assert dependency_loops(graph) == [["P1", "P2"]]
    issues = dependency_issues(graph, ["A", "B"])
    assert [(issue.puzzle_id, issue.index, issue.dependency_id, issue.kind) for issue in issues] == [
        ("P2", 1, "P9", "unknown"),
        ("P4", 0, "P3", "later_stage"),
    ]
    stages = [
        Stage(id="A", label="a", opens_with="start"),
        Stage(id="B", label="b", opens_with="P3"),
        Stage(id="C", label="c", opens_with="P8"),
    ]
    assert stage_opener_issues(stages, graph) == [(1, "order"), (2, "unknown")]
    flow = golden_game().flow
    assert final_puzzle_issue(flow, nodes(("P3", "B", ()))) is None
    assert final_puzzle_issue(flow, nodes(("P3", "A", ()))) == "stage"
    assert final_puzzle_issue(flow, []) == "unknown"
    assert final_puzzle_issue(flow.model_copy(update={"final_puzzle": None}), []) is None
