from typing import Any

from test_checks_support import edit_document, edit_flow, edit_story, golden_game, rules

from mystery_forge.checks.deduction import check_deduction, elimination_findings, hidden_clue_count_findings
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
    findings = check_deduction(with_deduction(exclusions=golden_deduction().exclusions[1:]))
    assert rules(findings) == ["deduction.suspect_not_excluded"]
    assert "Ana Ruiz" in findings[0].message
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
    assert "deduction.proof_unavailable" not in rules(check_deduction(unknown_id))


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


def hidden_clue(game: Game, clue_id: str, **updates: Any) -> Game:
    clues: list[Clue] = [clue.model_copy(update=updates) if clue.id == clue_id else clue for clue in game.story.clues]
    return edit_story(game, clues=clues)


def test_a_hidden_proof_clue_needs_no_document() -> None:
    assert rules(check_deduction(golden_game())) == []


def test_every_question_needs_a_clue_that_a_puzzle_reveals() -> None:
    who, why = golden_deduction().questions
    plain_why = why.model_copy(update={"proven_by": ["felix-debt"]})
    findings = check_deduction(with_deduction(questions=[who, plain_why]))
    assert rules(findings) == ["deduction.puzzles_not_needed"]
    assert (findings[0].file, findings[0].path, findings[0].severity) == (
        "story.yaml",
        "deduction.questions.1.proven_by",
        "error",
    )
    assert "'why'" in findings[0].message
    assert check_deduction(with_deduction(questions=[who])) == []


def test_a_hidden_clue_counts_only_when_an_existing_puzzle_reveals_it() -> None:
    for revealed_by in (None, "P9"):
        game: Game = hidden_clue(golden_game(), "came-by-boat", revealed_by=revealed_by)
        assert rules(check_deduction(game)) == ["deduction.puzzles_not_needed"]
    unknown_proof: Game = with_deduction(
        questions=[question.model_copy(update={"proven_by": ["ghost"]}) for question in golden_deduction().questions]
    )
    assert rules(check_deduction(unknown_proof)) == ["deduction.puzzles_not_needed"] * 2


def test_a_case_file_story_with_fewer_than_two_hidden_clues_gets_a_warning() -> None:
    story = golden_game().story
    config = golden_game().config
    assert hidden_clue_count_findings(story, config) == []
    one_hidden = story.model_copy(update={"clues": [clue for clue in story.clues if clue.id != "came-by-boat"]})
    findings = hidden_clue_count_findings(one_hidden, config)
    assert rules(findings) == ["deduction.few_hidden_clues"]
    assert (findings[0].file, findings[0].path, findings[0].severity) == ("story.yaml", "clues", "warning")
    assert hidden_clue_count_findings(one_hidden, config.model_copy(update={"format": "case_file"})) != []
    assert hidden_clue_count_findings(one_hidden, config.model_copy(update={"format": "envelopes"})) == []


def test_plain_clues_that_clear_every_innocent_suspect_name_the_culprit_by_elimination() -> None:
    plain_exclusions: list[Exclusion] = [
        exclusion.model_copy(update={"clues": [clue for clue in exclusion.clues if clue != "came-by-boat"]})
        for exclusion in golden_deduction().exclusions
    ]
    findings = check_deduction(with_deduction(exclusions=plain_exclusions))
    assert rules(findings) == ["deduction.culprit_by_elimination"]
    assert (findings[0].file, findings[0].path, findings[0].severity) == (
        "story.yaml",
        "deduction.exclusions",
        "error",
    )
    story = golden_game().story
    plain_story = story.model_copy(
        update={"deduction": golden_deduction().model_copy(update={"exclusions": plain_exclusions})}
    )
    assert rules(elimination_findings(plain_story)) == ["deduction.culprit_by_elimination"]
    assert elimination_findings(story) == []
    assert elimination_findings(story.model_copy(update={"deduction": None})) == []
