import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from mystery_forge.findings import Finding
from mystery_forge.plan import check_plan_folder

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"
IMPLEMENTED: frozenset[str] = frozenset({"caesar-cipher", "arithmetic-lock", "deduction", "anagram", "maze"})


def golden_plan() -> dict[str, Any]:
    return {
        "format_version": "1",
        "motif": "The tide table returns in every envelope.",
        "puzzles": [
            {
                "id": "P1",
                "stage": "A",
                "title": "The keeper's coded line",
                "mechanic": "caesar-cipher",
                "difficulty": "easy",
                "answer": "boathouse",
                "in_world_reason": "Tom hides his notes.",
                "hidden_from": "the crew",
                "reveals": "The keys are in the boathouse.",
                "documents": ["D2"],
            },
            {
                "id": "P2",
                "stage": "A",
                "title": "The store room lock",
                "mechanic": "arithmetic-lock",
                "difficulty": "easy",
                "answer": "0726",
                "in_world_reason": "A dial lock.",
                "hidden_from": "anyone without the receipt",
                "reveals": "The collector offered to forget the debt for a lens.",
                "documents": ["D3"],
                "relies_on": ["D1"],
            },
            {
                "id": "P3",
                "stage": "B",
                "title": "How did the thief reach the rock?",
                "mechanic": "deduction",
                "difficulty": "easy",
                "depends_on": ["P1"],
                "answer": "low tide",
                "in_world_reason": "The causeway floods.",
                "hidden_from": "anyone who does not know the tides",
                "reveals": "The thief came at low tide.",
                "documents": ["D4"],
            },
        ],
        "story_documents": [
            {"id": "D1", "kind": "letter", "stage": "A", "title": "A letter", "purpose": "Sets the case."},
            {
                "id": "D5",
                "kind": "generic",
                "stage": "B",
                "title": "Two papers",
                "purpose": "Clears Maud and shows the debt.",
                "must_contain": ["Return ticket, 15 March 1931, first ferry, 8:15"],
            },
        ],
    }


@pytest.fixture
def game_dir(tmp_path: Path) -> Path:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "source")
    write_plan(tmp_path, golden_plan())
    return tmp_path


def write_plan(game_dir: Path, plan: dict[str, Any]) -> None:
    (game_dir / "source" / "plan.yaml").write_text(yaml.safe_dump(plan, allow_unicode=True), encoding="utf-8")


def check(game_dir: Path) -> list[Finding]:
    return check_plan_folder(game_dir, implemented_builders=IMPLEMENTED)


def errors(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings if finding.severity == "error"]


def warnings(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings if finding.severity == "warning"]


def mutate(game_dir: Path, change: Any) -> list[Finding]:
    plan = golden_plan()
    change(plan)
    write_plan(game_dir, plan)
    return check(game_dir)


def test_the_golden_plan_has_no_errors(game_dir: Path) -> None:
    findings = check(game_dir)
    assert errors(findings) == []


def test_a_missing_plan_is_reported(game_dir: Path) -> None:
    (game_dir / "source" / "plan.yaml").unlink()
    assert errors(check(game_dir)) == ["source.missing"]


def test_a_broken_story_flow_or_config_stops_the_check(game_dir: Path) -> None:
    (game_dir / "source" / "flow.yaml").unlink()
    assert "source.missing" in errors(check(game_dir))


def test_plan_schema_errors_are_reported(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"difficulty": "trivial"}))
    assert errors(findings) == ["schema.literal_error"]


def test_duplicate_puzzle_and_document_ids(game_dir: Path) -> None:
    def duplicate(plan: dict[str, Any]) -> None:
        plan["puzzles"][1]["id"] = "P1"
        plan["puzzles"][1]["documents"] = ["D2"]

    rules = errors(mutate(game_dir, duplicate))
    assert "plan.duplicate_puzzle" in rules
    assert "plan.duplicate_document" in rules


def test_a_document_shared_by_a_puzzle_and_the_story_documents(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["story_documents"][0].update({"id": "D2"}))
    assert "plan.duplicate_document" in errors(findings)


def test_unknown_and_unimplemented_mechanics(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"mechanic": "caesar"}))
    assert errors(findings) == ["plan.mechanic_unknown"]
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"mechanic": "vigenere-cipher"}))
    assert errors(findings) == ["plan.mechanic_unavailable"]


def test_a_mechanic_that_does_not_fit_the_equipment(game_dir: Path) -> None:
    config_path = game_dir / "source" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["equipment"]["scissors"] = False
    config_path.write_text(json.dumps(config), encoding="utf-8")
    scissors_mechanic = "cut-strips"
    findings = check_plan_folder(game_dir, implemented_builders=IMPLEMENTED | {scissors_mechanic})
    assert errors(findings) == []
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"mechanic": scissors_mechanic}))
    findings = check_plan_folder(game_dir, implemented_builders=IMPLEMENTED | {scissors_mechanic})
    assert "plan.mechanic_unfit" in errors(findings)


def test_graph_errors(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"depends_on": ["P9"]}))
    assert errors(findings) == ["plan.dependency_unknown"]
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"depends_on": ["P3"]}))
    assert "plan.dependency_later_stage" in errors(findings)

    def cycle(plan: dict[str, Any]) -> None:
        plan["puzzles"][0]["depends_on"] = ["P2"]
        plan["puzzles"][1]["depends_on"] = ["P1"]

    assert errors(mutate(game_dir, cycle)) == ["plan.dependency_cycle"]
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"stage": "C"}))
    assert "plan.stage_unknown" in errors(findings)


def test_flow_must_open_stages_with_planned_earlier_puzzles(game_dir: Path) -> None:
    flow_path = game_dir / "source" / "flow.yaml"
    flow_path.write_text(flow_path.read_text(encoding="utf-8").replace("opens_with: P1", "opens_with: P3"), "utf-8")
    assert "plan.stage_opener" in errors(check(game_dir))
    flow_path.write_text(flow_path.read_text(encoding="utf-8").replace("opens_with: P3", "opens_with: P8"), "utf-8")
    assert "plan.stage_opener" in errors(check(game_dir))


def test_the_final_puzzle_must_exist_and_sit_in_the_last_stage(game_dir: Path) -> None:
    flow_path = game_dir / "source" / "flow.yaml"
    flow_path.write_text(flow_path.read_text(encoding="utf-8").replace("final_puzzle: P3", "final_puzzle: P2"), "utf-8")
    assert errors(check(game_dir)) == ["plan.final_puzzle"]
    flow_path.write_text(flow_path.read_text(encoding="utf-8").replace("final_puzzle: P2", "final_puzzle: P7"), "utf-8")
    assert errors(check(game_dir)) == ["plan.final_puzzle"]


def test_every_stage_needs_a_document(game_dir: Path) -> None:
    def remove_stage_b_documents(plan: dict[str, Any]) -> None:
        plan["puzzles"][2]["documents"] = ["D4"]
        plan["puzzles"][2]["stage"] = "A"
        plan["puzzles"][2]["depends_on"] = []
        plan["story_documents"][1]["stage"] = "A"

    flow_path = game_dir / "source" / "flow.yaml"
    flow_path.write_text(flow_path.read_text(encoding="utf-8").replace("final_puzzle: P3", "final_puzzle: P2"), "utf-8")
    assert "plan.stage_empty" in errors(mutate(game_dir, remove_stage_b_documents))


def test_story_clues_must_point_to_planned_documents(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["story_documents"].pop(1))
    assert "plan.clue_document" in errors(findings)


def test_relies_on_must_name_a_story_document_of_the_same_or_an_earlier_stage(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["puzzles"][1].update({"relies_on": ["D9"]}))
    assert errors(findings) == ["plan.relies_on"]
    findings = mutate(game_dir, lambda plan: plan["puzzles"][1].update({"relies_on": ["D5"]}))
    assert errors(findings) == ["plan.relies_on"]


def test_variety_rules(game_dir: Path) -> None:
    def three_ciphers(plan: dict[str, Any]) -> None:
        for puzzle in plan["puzzles"]:
            puzzle["mechanic"] = "caesar-cipher"
            puzzle["difficulty"] = "easy"

    findings = mutate(game_dir, three_ciphers)
    assert "plan.lookup_ciphers" in errors(findings)
    assert "plan.same_mechanic" in warnings(findings)
    assert "plan.same_action_in_a_row" in warnings(findings)
    assert "plan.few_actions" in warnings(findings)


def test_puzzle_count_and_budget_warnings(game_dir: Path) -> None:
    def many(plan: dict[str, Any]) -> None:
        for number in range(4, 12):
            plan["puzzles"].append(
                plan["puzzles"][1] | {"id": f"P{number}", "documents": [f"D{number + 10}"], "relies_on": []}
            )

    findings = mutate(game_dir, many)
    assert "plan.puzzle_count" in warnings(findings)
    assert "plan.budget" in [finding.rule for finding in findings]


def test_the_plan_budget_counts_the_reading_budget_of_the_brief(game_dir: Path) -> None:
    brief_path = game_dir / "source" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["reading_words"] = 20000
    brief_path.write_text(json.dumps(brief), encoding="utf-8")
    findings = [finding for finding in check(game_dir) if finding.rule == "plan.budget"]
    assert [finding.severity for finding in findings] == ["error"]
    # 5 + 5 + 10 catalog minutes, 20000 words read at 120 a minute by 2 players, 2 envelopes of 5 minutes.
    assert "about 113 minutes" in findings[0].message


def test_two_puzzles_with_the_same_mechanic_are_fine(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["puzzles"][1].update({"mechanic": "caesar-cipher"}))
    assert "plan.same_mechanic" not in warnings(findings)


def test_every_planned_puzzle_needs_a_hidden_from(game_dir: Path) -> None:
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].pop("hidden_from"))
    assert errors(findings) == ["schema.missing"]
    findings = mutate(game_dir, lambda plan: plan["puzzles"][0].update({"hidden_from": ""}))
    assert errors(findings) == ["schema.string_too_short"]


def replace_in_story(game_dir: Path, old: str, new: str) -> None:
    story_path = game_dir / "source" / "story.yaml"
    story_path.write_text(story_path.read_text(encoding="utf-8").replace(old, new), "utf-8")


def test_every_hidden_story_clue_needs_a_planned_revealing_puzzle(game_dir: Path) -> None:
    replace_in_story(game_dir, "revealed_by: P2", "revealed_by: P7")
    findings = [finding for finding in check(game_dir) if finding.rule == "plan.hidden_clue_unplanned"]
    assert [finding.severity for finding in findings] == ["error"]
    assert "lens-for-the-debt" in findings[0].message and "P7" in findings[0].message
    replace_in_story(game_dir, "    revealed_by: P7\n", "")
    assert "plan.hidden_clue_unplanned" in errors(check(game_dir))


def test_a_puzzle_without_a_job_is_a_dead_end(game_dir: Path) -> None:
    replace_in_story(game_dir, "revealed_by: P2", "revealed_by: P1")
    findings = [finding for finding in check(game_dir) if finding.rule == "plan.dead_end"]
    assert [finding.severity for finding in findings] == ["error"]
    assert "P2" in findings[0].message
    flow_path = game_dir / "source" / "flow.yaml"
    flow_path.write_text(flow_path.read_text(encoding="utf-8").replace("final_puzzle: P3", "final_puzzle: P2"), "utf-8")
    assert errors(check(game_dir)) == ["plan.final_puzzle"]


def test_the_same_action_rule_follows_the_code_order_not_the_file_order(game_dir: Path) -> None:
    def decode_last_in_file(plan: dict[str, Any]) -> None:
        plan["puzzles"][2]["mechanic"] = "caesar-cipher"
        plan["puzzles"] = [plan["puzzles"][0], plan["puzzles"][2], plan["puzzles"][1]]

    assert "plan.same_action_in_a_row" not in warnings(mutate(game_dir, decode_last_in_file))
