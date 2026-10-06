from typing import Any

from test_checks_support import edit_document, edit_flow, edit_story, golden_game, rules

from mystery_forge.checks.deduction import check_deduction
from mystery_forge.game import Game
from mystery_forge.spec.models import AccusationOption, Character, Clue, Deduction, Exclusion


def golden_deduction() -> Deduction:
    deduction: Deduction | None = golden_game().story.deduction
    assert deduction is not None
    return deduction


def with_deduction(game: Game | None = None, **updates: Any) -> Game:
    return edit_story(game or golden_game(), deduction=golden_deduction().model_copy(update=updates))


def with_character(index: int, **updates: Any) -> Game:
    characters: list[Character] = list(golden_game().story.characters)
    characters[index] = characters[index].model_copy(update=updates)
    return edit_story(golden_game(), characters=characters)


def test_the_golden_deduction_has_no_findings() -> None:
    assert check_deduction(golden_game()) == []


def test_no_deduction_is_fine_without_an_accusation_and_an_error_with_one() -> None:
    no_deduction: Game = edit_story(golden_game(), deduction=None)
    findings = check_deduction(no_deduction)
    assert rules(findings) == ["deduction.missing"]
    assert (findings[0].file, findings[0].path) == ("story.yaml", "deduction")
    assert check_deduction(edit_flow(no_deduction, accusation=False)) == []


def test_the_culprit_must_be_a_suspect() -> None:
    findings = check_deduction(with_character(2, is_suspect=False))
    assert rules(findings) == ["deduction.culprit_not_suspect"]
    assert findings[0].path == "characters.2.is_suspect"


def test_every_innocent_suspect_needs_an_exclusion() -> None:
    findings = check_deduction(with_deduction(exclusions=golden_deduction().exclusions[:1]))
    assert rules(findings) == ["deduction.suspect_not_excluded"]
    assert "Maud Price" in findings[0].message
    assert findings[0].severity == "error"


def test_an_exclusion_must_name_an_existing_innocent_suspect() -> None:
    exclusions: list[Exclusion] = [
        *golden_deduction().exclusions,
        Exclusion(suspect="ghost", clues=["wet-boots"], explanation="x"),
        Exclusion(suspect="felix-ward", clues=["wet-boots"], explanation="x"),
    ]
    findings = check_deduction(with_deduction(exclusions=exclusions))
    assert rules(findings) == ["deduction.unknown_suspect", "deduction.excludes_culprit"]
    assert [finding.path for finding in findings] == [
        "deduction.exclusions.2.suspect",
        "deduction.exclusions.3.suspect",
    ]


def test_a_proof_clue_must_be_in_a_document_of_the_game() -> None:
    clues: list[Clue] = list(golden_game().story.clues)
    clues[3] = clues[3].model_copy(update={"document": "D9"})
    game: Game = edit_story(golden_game(), clues=clues)
    hidden: Game = edit_document(golden_game(), "D5", meta={"stage": "F"})
    unknown_id: Game = with_deduction(
        questions=[golden_deduction().questions[0].model_copy(update={"proven_by": ["x"]})]
    )
    assert [finding.path for finding in check_deduction(game)] == [
        "deduction.questions.0.proven_by.1",
        "deduction.questions.1.proven_by.0",
    ]
    assert rules(check_deduction(hidden)) == ["deduction.proof_unavailable"] * 3
    assert check_deduction(unknown_id) == []


def test_a_question_should_offer_one_option_per_suspect() -> None:
    who = golden_deduction().questions[0]
    vague: list[AccusationOption] = [
        AccusationOption(id="cook", text="The cook"),
        AccusationOption(id="felix", text="Felix"),
        AccusationOption(id="inspector", text="The inspector"),
    ]
    findings = check_deduction(with_deduction(questions=[who.model_copy(update={"options": vague})]))
    assert rules(findings) == ["deduction.no_who_question"]
    assert findings[0].severity == "warning"
    by_alias: list[AccusationOption] = [*vague[:2], AccusationOption(id="x", text="Inspector Price")]
    characters: list[Character] = list(golden_game().story.characters)
    characters[3] = characters[3].model_copy(update={"aliases": ["Inspector Price"]})
    aliased: Game = edit_story(golden_game(), characters=characters)
    ids_match: list[AccusationOption] = [
        AccusationOption(id="ana-ruiz", text="The cook"),
        AccusationOption(id="felix", text="The boatman"),
        AccusationOption(id="maud", text="The inspector"),
    ]
    vague_cook: Game = with_deduction(aliased, questions=[who.model_copy(update={"options": by_alias})])
    assert rules(check_deduction(vague_cook)) == ["deduction.no_who_question"]
    named_cook: list[AccusationOption] = [AccusationOption(id="ana", text="x"), *by_alias[1:]]
    assert check_deduction(with_deduction(aliased, questions=[who.model_copy(update={"options": named_cook})])) == []
    assert check_deduction(with_deduction(questions=[who.model_copy(update={"options": ids_match})])) == []


def test_a_game_without_suspects_needs_no_who_question() -> None:
    characters: list[Character] = [
        character.model_copy(update={"is_suspect": False}) for character in golden_game().story.characters
    ]
    game: Game = edit_story(golden_game(), characters=characters)
    assert rules(check_deduction(game)) == ["deduction.culprit_not_suspect"]
