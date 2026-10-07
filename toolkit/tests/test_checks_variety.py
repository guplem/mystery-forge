from typing import Any

from test_checks_support import edit_config, edit_flow, edit_puzzle, golden_game, golden_mechanics, only_rule, rules

from mystery_forge.catalog import Mechanic
from mystery_forge.checks.variety import (
    check_variety,
    lookup_cipher_ids,
    missing_player_actions,
    overused_mechanics,
    same_action_pairs,
)
from mystery_forge.game import Game
from mystery_forge.spec.models import SolutionStep


def changed_mechanic(mechanic_id: str, **updates: Any) -> dict[str, Mechanic]:
    mechanics: dict[str, Mechanic] = golden_mechanics()
    mechanics[mechanic_id] = mechanics[mechanic_id].model_copy(update=updates)
    return mechanics


def all_caesar(count: int) -> Game:
    game: Game = golden_game()
    for puzzle_id in ("P1", "P2", "P3")[:count]:
        game = edit_puzzle(game, puzzle_id, mechanic="caesar-cipher")
    return game


def test_the_golden_variety_only_warns_about_the_final_puzzle_and_cross_document_clues() -> None:
    findings = check_variety(golden_game(), golden_mechanics())
    assert rules(findings) == ["variety.final_not_meta", "variety.cross_document"]
    assert all(finding.severity == "warning" for finding in findings)
    assert (findings[0].file, findings[0].path) == ("puzzles/P3.yaml", "is_meta")


def test_a_mechanic_outside_the_catalog_is_an_error() -> None:
    findings = check_variety(edit_puzzle(golden_game(), "P1", mechanic="no-such-mechanic"), golden_mechanics())
    unknown = only_rule(findings, "variety.unknown_mechanic")
    assert [(finding.file, finding.path, finding.severity) for finding in unknown] == [
        ("puzzles/P1.yaml", "mechanic", "error")
    ]


def test_a_mechanic_must_fit_the_equipment() -> None:
    needs = golden_mechanics()["caesar-cipher"].needs.model_copy(update={"scissors": True, "tape": True, "color": True})
    mechanics: dict[str, Mechanic] = changed_mechanic("caesar-cipher", needs=needs)
    assert rules(only_rule(check_variety(golden_game(), mechanics), "variety.equipment")) == ["variety.equipment"]
    bare: Game = edit_config(golden_game(), "equipment", scissors=False, printer="black_and_white")
    findings = only_rule(check_variety(bare, mechanics), "variety.equipment")
    assert len(findings) == 3
    assert {finding.severity for finding in findings} == {"error"}
    assert "scissors" in findings[0].message


def test_a_mechanic_for_another_audience_is_a_warning() -> None:
    mechanics: dict[str, Mechanic] = changed_mechanic("caesar-cipher", audiences=("adults",))
    findings = only_rule(check_variety(golden_game(), mechanics), "variety.audience")
    assert [(finding.file, finding.severity) for finding in findings] == [("puzzles/P1.yaml", "warning")]


def test_too_few_player_actions_and_the_same_action_twice_in_a_row_are_warnings() -> None:
    findings = check_variety(all_caesar(2), golden_mechanics())
    assert rules(findings)[:2] == ["variety.player_actions", "variety.same_action_in_a_row"]
    assert findings[1].file == "puzzles/P2.yaml"


def test_more_than_two_lookup_ciphers_is_an_error_and_a_third_same_mechanic_a_warning() -> None:
    findings = check_variety(all_caesar(3), golden_mechanics())
    assert only_rule(findings, "variety.lookup_ciphers")[0].severity == "error"
    assert only_rule(findings, "variety.repeated_mechanic")[0].severity == "warning"


def test_a_meta_final_puzzle_or_one_with_two_dependencies_is_fine() -> None:
    meta: Game = edit_puzzle(golden_game(), "P3", is_meta=True)
    assert only_rule(check_variety(meta, golden_mechanics()), "variety.final_not_meta") == []
    wide: Game = edit_puzzle(golden_game(), "P3", depends_on=["P1", "P2"])
    assert only_rule(check_variety(wide, golden_mechanics()), "variety.final_not_meta") == []
    for final in (None, "P9"):
        game: Game = edit_flow(golden_game(), final_puzzle=final)
        assert only_rule(check_variety(game, golden_mechanics()), "variety.final_not_meta") == []


def test_enough_puzzles_that_combine_documents_clear_the_cross_document_warning() -> None:
    steps: list[SolutionStep] = [SolutionStep(text="Combine.", uses=["coded-line", "receipt-lines", "ghost"])]
    game: Game = edit_puzzle(golden_game(), "P1", solution=steps)
    assert only_rule(check_variety(game, golden_mechanics()), "variety.cross_document") == []
    empty: Game = golden_game().model_copy(update={"puzzles": []})
    assert check_variety(empty, golden_mechanics()) == []


def test_a_meta_final_puzzle_must_use_an_answer_of_every_earlier_stage_in_an_envelope_game() -> None:
    meta: Game = edit_puzzle(golden_game(), "P3", is_meta=True, depends_on=[])
    findings = only_rule(check_variety(meta, golden_mechanics()), "variety.final_not_meta")
    assert [(finding.file, finding.path, finding.severity) for finding in findings] == [
        ("puzzles/P3.yaml", "depends_on", "warning")
    ]
    assert "A" in findings[0].message
    case_file: Game = meta.model_copy(update={"config": meta.config.model_copy(update={"format": "case_file"})})
    assert only_rule(check_variety(case_file, golden_mechanics()), "variety.final_not_meta") == []
    plain: Game = edit_puzzle(golden_game(), "P3", depends_on=[])
    assert [
        finding.path for finding in only_rule(check_variety(plain, golden_mechanics()), "variety.final_not_meta")
    ] == [
        "is_meta",
        "depends_on",
    ]


def test_the_shared_variety_rules_work_on_plain_puzzle_data() -> None:
    mechanics: dict[str, Mechanic] = golden_mechanics()
    caesar: Mechanic = mechanics["caesar-cipher"]
    lock: Mechanic = mechanics["arithmetic-lock"]
    three_ciphers = [("P1", caesar), ("P2", caesar), ("P3", caesar)]
    assert lookup_cipher_ids(three_ciphers) == ["P1", "P2", "P3"]
    assert lookup_cipher_ids(three_ciphers[:2]) == []
    assert overused_mechanics(three_ciphers) == {"caesar-cipher": 3}
    assert overused_mechanics(three_ciphers[:2]) == {}
    assert missing_player_actions(three_ciphers, 3) == 3
    assert missing_player_actions([("P1", caesar), ("P2", lock)], 2) is None
    assert same_action_pairs([("P1", caesar), ("P2", caesar), ("P3", lock), ("P4", caesar)]) == [("P1", "P2")]
