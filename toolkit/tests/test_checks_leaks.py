from test_checks_support import (
    edit_assembled_puzzle,
    edit_document,
    edit_flow,
    edit_puzzle,
    edit_story,
    golden_game,
    only_rule,
    rules,
)

from mystery_forge.checks.leaks import check_leaks
from mystery_forge.game import Game
from mystery_forge.mechanics.base import Artifact
from mystery_forge.spec.models import AnswerFormat, LeakAllowance


def with_text(game: Game, document_id: str, extra: str) -> Game:
    document = next(document for document in game.documents if document.meta.id == document_id)
    return edit_document(game, document_id, text=f"{document.text}\n\n{extra}")


def test_the_golden_game_leaks_no_answer() -> None:
    assert check_leaks(golden_game()) == []


def test_an_answer_spelled_with_separators_in_an_earlier_document_is_an_error() -> None:
    findings = check_leaks(with_text(golden_game(), "D1", "The dial shows 0-7-2 6."))
    assert rules(findings) == ["leaks.answer_in_text"]
    # The finding goes to the puzzle file: its owner can change the answer or allow the passage there.
    assert (findings[0].file, findings[0].severity) == ("puzzles/P2.yaml", "error")
    assert "P2" in findings[0].message
    assert "documents/D1.md" in findings[0].message
    assert findings[0].fix_hint


def test_a_reversed_answer_is_a_leak() -> None:
    findings = check_leaks(with_text(golden_game(), "D3", "Batch 6270."))
    assert rules(findings) == ["leaks.answer_in_text"]
    assert "reversed" in findings[0].message


def test_a_palindrome_answer_is_reported_once() -> None:
    game: Game = edit_assembled_puzzle(golden_game(), "P1", accepted_normalized=["level"])
    assert len(check_leaks(with_text(game, "D1", "Keep it level."))) == 1


def test_documents_of_later_stages_do_not_count() -> None:
    assert check_leaks(with_text(golden_game(), "D5", "The boathouse key.")) == []


def test_documents_in_an_unknown_stage_and_puzzles_in_an_unknown_stage_are_skipped() -> None:
    hidden: Game = edit_document(with_text(golden_game(), "D1", "boathouse"), "D1", meta={"stage": "F"})
    assert check_leaks(hidden) == []
    lost: Game = edit_puzzle(with_text(golden_game(), "D1", "boathouse"), "P1", stage="F")
    assert check_leaks(lost) == []


def test_the_puzzle_s_own_artifact_text_does_not_count_but_another_artifact_does() -> None:
    own: Game = edit_assembled_puzzle(
        golden_game(), "P1", artifact=Artifact(html="<p>x</p>", solver_text="KEYS IN THE BOATHOUSE")
    )
    assert check_leaks(with_text(own, "D2", "KEYS IN THE BOATHOUSE")) == []
    other: Game = edit_assembled_puzzle(
        golden_game(), "P2", artifact=Artifact(html="<p>x</p>", solver_text="BOATHOUSE")
    )
    findings = check_leaks(with_text(other, "D3", "BOATHOUSE"))
    assert [finding.file for finding in findings] == ["puzzles/P1.yaml"]


def test_name_and_choice_answers_are_not_leak_checked() -> None:
    game: Game = edit_puzzle(golden_game(), "P1", answer_format=AnswerFormat(kind="name", label="a place"))
    assert check_leaks(with_text(game, "D1", "boathouse")) == []


def test_a_short_answer_is_a_warning_and_is_not_searched() -> None:
    game: Game = edit_assembled_puzzle(golden_game(), "P2", accepted_normalized=["07", "eleven"])
    findings = check_leaks(with_text(game, "D1", "07 and eleven"))
    assert rules(findings) == ["leaks.short_answer", "leaks.answer_in_text"]
    assert (findings[0].severity, findings[0].path) == ("warning", "answer")


def test_an_allowlisted_text_suppresses_the_leak_and_an_unused_entry_is_a_warning() -> None:
    allowed = LeakAllowance(text="the old boathouse", reason="The boathouse is a known place.")
    game: Game = edit_puzzle(golden_game(), "P1", leak_allowlist=[allowed])
    assert check_leaks(with_text(game, "D1", "Meet me at The Old Boathouse.")) == []
    findings = check_leaks(game)
    assert rules(findings) == ["leaks.allowlist_unused"]
    assert (findings[0].path, findings[0].severity) == ("leak_allowlist.0.text", "warning")


def test_an_answer_in_a_title_or_a_header_field_is_an_error() -> None:
    game: Game = edit_puzzle(golden_game(), "P1", title="The boathouse code")
    game = edit_document(game, "D3", meta={"title": "Boathouse receipt", "fields": {"sender": "Boathouse Ltd"}})
    findings = check_leaks(game)
    assert rules(findings) == ["leaks.answer_in_title"] * 3
    assert [(finding.file, finding.path) for finding in findings] == [
        ("documents/D3.md", "title"),
        ("documents/D3.md", "fields.sender"),
        ("puzzles/P1.yaml", "title"),
    ]


def test_the_intro_and_the_opening_texts_up_to_the_stage_count() -> None:
    intro: Game = edit_story(golden_game(), intro="Start in the boathouse.")
    findings = check_leaks(intro)
    assert [(finding.file, finding.path) for finding in findings] == [("story.yaml", "intro")]
    stages = list(golden_game().flow.stages)
    opening: Game = edit_flow(
        golden_game(), stages=[stages[0], stages[1].model_copy(update={"opening_text": "Low tide, boathouse."})]
    )
    findings = check_leaks(opening)
    assert [(finding.file, finding.path, "P3" in finding.message) for finding in findings] == [
        ("flow.yaml", "stages.1.opening_text", True)
    ]


def test_a_hidden_clue_written_out_before_its_puzzle_is_a_warning() -> None:
    boat: str = "The THIEF crossed to the rock at low tide, and carried the lens back to a boat!"
    findings = only_rule(check_leaks(with_text(golden_game(), "D5", boat)), "leaks.hidden_clue_in_text")
    assert len(findings) == 1
    assert (findings[0].file, findings[0].severity) == ("documents/D5.md", "warning")
    assert "came-by-boat" in findings[0].message and "P3" in findings[0].message
    debt: str = "The collector offered to forget the debt of Felix in exchange for a lighthouse lens."
    assert rules(check_leaks(with_text(golden_game(), "D1", debt))) == ["leaks.hidden_clue_in_text"]
    assert check_leaks(with_text(golden_game(), "D4", debt)) == []


def test_a_hidden_clue_without_a_known_revealing_puzzle_is_left_to_the_ledger() -> None:
    clues = [
        clue.model_copy(update={"revealed_by": "P9"}) if clue.hidden else clue for clue in golden_game().story.clues
    ]
    boat: str = "The thief crossed to the rock at low tide and carried the lens back to a boat."
    game: Game = with_text(edit_story(golden_game(), clues=clues), "D1", boat)
    assert only_rule(check_leaks(game), "leaks.hidden_clue_in_text") == []
    unknown_stage: Game = with_text(edit_puzzle(golden_game(), "P3", stage="F"), "D1", boat)
    assert only_rule(check_leaks(unknown_stage), "leaks.hidden_clue_in_text") == []
