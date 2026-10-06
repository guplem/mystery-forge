from test_checks_support import (
    edit_assembled_puzzle,
    edit_document,
    edit_flow,
    edit_puzzle,
    golden_game,
    only_rule,
    rules,
)

from mystery_forge.checks.graph import check_graph
from mystery_forge.game import Game
from mystery_forge.mechanics.base import Artifact
from mystery_forge.spec.models import Stage


def test_the_golden_graph_has_no_findings() -> None:
    assert check_graph(golden_game()) == []


def test_a_puzzle_or_document_in_an_unknown_stage_is_an_error() -> None:
    game: Game = edit_puzzle(golden_game(), "P2", stage="F")
    game = edit_document(game, "D5", meta={"stage": "G"})
    findings = only_rule(check_graph(game), "graph.unknown_stage")
    assert [(finding.file, finding.path) for finding in findings] == [
        ("puzzles/P2.yaml", "stage"),
        ("documents/D5.md", "stage"),
    ]
    assert all(finding.severity == "error" and finding.fix_hint for finding in findings)


def test_an_unknown_dependency_is_an_error_and_does_not_block_reachability() -> None:
    findings = check_graph(edit_puzzle(golden_game(), "P3", depends_on=["P1", "P9"]))
    assert rules(findings) == ["graph.unknown_dependency"]
    assert findings[0].path == "depends_on.1"
    assert "P9" in findings[0].message


def test_a_dependency_in_a_later_stage_is_an_error() -> None:
    findings = check_graph(edit_puzzle(golden_game(), "P2", depends_on=["P3"]))
    assert rules(findings) == ["graph.dependency_later_stage"]
    assert findings[0].file == "puzzles/P2.yaml"
    assert findings[0].path == "depends_on.0"


def test_a_dependency_loop_is_one_error_per_loop() -> None:
    game: Game = edit_puzzle(golden_game(), "P1", depends_on=["P2"])
    game = edit_puzzle(game, "P2", depends_on=["P1"])
    findings = check_graph(game)
    loops = only_rule(findings, "graph.dependency_loop")
    assert len(loops) == 1
    assert loops[0].file == "puzzles/P1.yaml"
    assert "P1, P2" in loops[0].message
    assert len(only_rule(findings, "graph.unreachable")) == 3


def test_a_puzzle_that_depends_on_itself_is_a_loop() -> None:
    findings = only_rule(check_graph(edit_puzzle(golden_game(), "P2", depends_on=["P2"])), "graph.dependency_loop")
    assert [finding.file for finding in findings] == ["puzzles/P2.yaml"]


def test_a_stage_that_opens_with_an_unknown_or_later_puzzle_is_an_error() -> None:
    stages: list[Stage] = list(golden_game().flow.stages)
    unknown: Game = edit_flow(golden_game(), stages=[stages[0], stages[1].model_copy(update={"opens_with": "P7"})])
    findings = check_graph(unknown)
    assert rules(findings)[0] == "graph.opens_with_unknown"
    assert findings[0].file == "flow.yaml"
    assert findings[0].path == "stages.1.opens_with"
    same_stage: Game = edit_flow(golden_game(), stages=[stages[0], stages[1].model_copy(update={"opens_with": "P3"})])
    assert "graph.opens_with_order" in rules(check_graph(same_stage))


def test_an_opening_puzzle_in_an_unknown_stage_is_reported_only_once() -> None:
    findings = check_graph(edit_puzzle(golden_game(), "P1", stage="F"))
    assert "graph.opens_with_order" not in rules(findings)
    assert "graph.unknown_stage" in rules(findings)


def test_a_puzzle_in_a_stage_that_never_opens_is_unreachable() -> None:
    stages: list[Stage] = list(golden_game().flow.stages)
    game: Game = edit_flow(golden_game(), stages=[stages[0], stages[1].model_copy(update={"opens_with": "P3"})])
    unreachable = only_rule(check_graph(game), "graph.unreachable")
    assert [finding.file for finding in unreachable] == ["puzzles/P3.yaml"]
    assert "never opens" in unreachable[0].message


def test_the_final_puzzle_must_exist_and_sit_in_the_last_stage() -> None:
    unknown = check_graph(edit_flow(golden_game(), final_puzzle="P8"))
    assert rules(unknown) == ["graph.final_puzzle_unknown"]
    assert unknown[0].path == "final_puzzle"
    early = check_graph(edit_flow(golden_game(), final_puzzle="P2"))
    assert rules(early) == ["graph.final_puzzle_stage"]
    assert check_graph(edit_flow(golden_game(), final_puzzle=None)) == []


def test_a_funnel_final_puzzle_must_depend_on_every_earlier_stage() -> None:
    funnel: Game = edit_flow(golden_game(), structure="funnel")
    assert check_graph(funnel) == []
    missing = check_graph(edit_puzzle(funnel, "P3", depends_on=[]))
    assert rules(missing) == ["graph.funnel_missing_stage"]
    assert "A" in missing[0].message
    in_unknown_stage = check_graph(edit_puzzle(funnel, "P3", stage="F"))
    assert "graph.funnel_missing_stage" not in rules(in_unknown_stage)


def test_a_funnel_counts_transitive_dependencies() -> None:
    stages: list[Stage] = list(golden_game().flow.stages)
    stage_c = Stage(id="C", label="The tower", opens_with="P3")
    game: Game = edit_flow(golden_game(), structure="funnel", stages=[*stages, stage_c], final_puzzle="P2")
    game = edit_puzzle(game, "P2", stage="C", depends_on=["P3"])
    game = edit_document(game, "D3", meta={"stage": "C"})
    assert check_graph(game) == []


def test_a_stage_without_documents_and_an_unknown_document_puzzle_are_errors() -> None:
    game: Game = edit_document(golden_game(), "D4", meta={"stage": "A", "puzzle": None})
    game = edit_document(game, "D5", meta={"stage": "A", "puzzle": "P6"})
    findings = check_graph(game)
    assert rules(findings) == ["graph.stage_without_documents", "graph.unknown_puzzle"]
    assert findings[0].path == "stages.1"
    assert (findings[1].file, findings[1].path) == ("documents/D5.md", "puzzle")


def test_too_few_free_puzzles_in_the_first_stage_is_a_warning() -> None:
    wide: Game = golden_game().model_copy(
        update={"brief": golden_game().brief.model_copy(update={"parallel_width": 2})}
    )
    assert check_graph(wide) == []
    findings = check_graph(edit_puzzle(wide, "P2", depends_on=["P1"]))
    assert rules(findings) == ["graph.parallel_width"]
    assert findings[0].severity == "warning"


def test_a_built_artifact_must_sit_in_exactly_one_document() -> None:
    missing = check_graph(edit_document(golden_game(), "D2", body_html="<p>no mark</p>"))
    assert rules(missing) == ["graph.artifact_missing"]
    assert missing[0].file == "puzzles/P1.yaml"
    twice: Game = edit_document(golden_game(), "D5", body_html="<p>⟦artifact:P1⟧</p>")
    duplicated = check_graph(twice)
    assert rules(duplicated) == ["graph.artifact_duplicated"]
    assert "D2, D5" in duplicated[0].message


def test_an_empty_or_missing_artifact_needs_no_document() -> None:
    no_html: Game = edit_assembled_puzzle(golden_game(), "P1", artifact=Artifact(html="", solver_text=""))
    assert check_graph(edit_document(no_html, "D2", body_html="")) == []
    no_artifact: Game = edit_assembled_puzzle(golden_game(), "P1", artifact=None)
    assert check_graph(edit_document(no_artifact, "D2", body_html="")) == []
