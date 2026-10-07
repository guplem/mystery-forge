from typing import Any

import pytest
from pydantic import ValidationError

from mystery_forge.spec.models import Clue, DocumentMeta, Flow, Puzzle, Story


def minimal_story() -> dict[str, Any]:
    return {
        "format_version": "1",
        "title": "The Last Lamp",
        "tagline": "A keeper vanished.",
        "premise": "The lamp went dark at midnight.",
        "setting": "A lighthouse",
        "era": "1920s",
        "tone": "cozy",
        "truth": "The cook did it.",
        "characters": [
            {"id": "ana-ruiz", "name": "Ana Ruiz", "role": "cook", "description": "Quiet.", "is_suspect": "true"},
            {"id": "tom-bell", "name": "Tom Bell", "role": "keeper", "description": "Loud.", "age": "54"},
        ],
        "intro": "Welcome.",
        "epilogues": [{"id": "solved", "min_score_percent": "70", "title": "Case closed", "text": "Well done."}],
    }


def minimal_puzzle() -> dict[str, Any]:
    return {
        "format_version": "1",
        "id": "P1",
        "title": "The coded note",
        "stage": "A",
        "mechanic": "caesar-cipher",
        "difficulty": "easy",
        "in_world_reason": "The keeper hid his notes from the crew.",
        "reveals": "The meeting place.",
        "answer": "Old Mill",
        "answer_format": {"kind": "phrase", "label": "two words"},
        "params": {"shift": "3"},
        "clues": [{"id": "note-shift", "document": "D1", "quote": "three steps back"}],
        "solution": [{"text": "Shift every letter back by three.", "uses": ["note-shift"]}],
        "hints": [
            {"level": "1", "text": "Look at the note.", "points_to": ["note-shift"]},
            {"level": "2", "text": "Count the steps.", "points_to": ["note-shift"]},
        ],
        "canary": "canary-7f3a",
    }


def test_a_minimal_story_loads_and_converts_text_values() -> None:
    story = Story.model_validate(minimal_story())
    assert story.characters[0].is_suspect is True
    assert story.characters[1].age == 54
    assert story.epilogues[0].min_score_percent == 70
    assert story.deduction is None


def test_story_rejects_unknown_fields_and_other_versions() -> None:
    data = minimal_story() | {"surprise": "x"}
    with pytest.raises(ValidationError, match="surprise"):
        Story.model_validate(data)
    with pytest.raises(ValidationError, match="format_version"):
        Story.model_validate(minimal_story() | {"format_version": "2"})


def test_story_rejects_bad_and_duplicate_registry_ids() -> None:
    data = minimal_story()
    data["characters"][0]["id"] = "Ana Ruiz"
    with pytest.raises(ValidationError, match="id"):
        Story.model_validate(data)
    data = minimal_story()
    data["locations"] = [{"id": "ana-ruiz", "name": "Kitchen", "description": "Warm."}]
    with pytest.raises(ValidationError, match="ana-ruiz"):
        Story.model_validate(data)


def test_story_deduction_must_name_the_one_culprit() -> None:
    data = minimal_story()
    data["characters"][0]["is_culprit"] = "true"
    data["clues"] = [{"id": "flour", "document": "D2", "quote": "flour on the stairs"}]
    data["deduction"] = {
        "culprit": "tom-bell",
        "questions": [
            {
                "id": "who",
                "prompt": "Who did it?",
                "options": [{"id": "ana", "text": "Ana"}, {"id": "tom", "text": "Tom"}],
                "correct": "ana",
                "points": "40",
                "proven_by": ["flour"],
            }
        ],
        "exclusions": [],
    }
    with pytest.raises(ValidationError, match="culprit"):
        Story.model_validate(data)
    data["deduction"]["culprit"] = "ana-ruiz"
    story = Story.model_validate(data)
    assert story.deduction is not None
    assert story.deduction.questions[0].points == 40


def test_story_with_two_culprits_is_invalid() -> None:
    data = minimal_story()
    for character in data["characters"]:
        character["is_culprit"] = "true"
    with pytest.raises(ValidationError, match="culprit"):
        Story.model_validate(data)


def test_story_clue_ids_are_unique() -> None:
    data = minimal_story()
    data["clues"] = [
        {"id": "flour", "document": "D2", "quote": "flour"},
        {"id": "flour", "document": "D3", "quote": "more flour"},
    ]
    with pytest.raises(ValidationError, match="flour"):
        Story.model_validate(data)


def test_a_plain_clue_quotes_a_document_and_is_not_hidden() -> None:
    clue = Clue.model_validate({"id": "flour", "document": "D2", "quote": "flour"})
    assert clue.hidden is False
    assert clue.revealed_by is None
    with pytest.raises(ValidationError, match="needs a document"):
        Clue.model_validate({"id": "flour", "quote": "flour"})
    with pytest.raises(ValidationError, match="revealed_by"):
        Clue.model_validate({"id": "flour", "document": "D2", "quote": "flour", "revealed_by": "P1"})


def test_a_hidden_clue_has_no_document_and_may_wait_for_its_revealing_puzzle() -> None:
    waiting = Clue.model_validate({"id": "came-by-boat", "hidden": "true", "quote": "The thief came by boat."})
    assert waiting.document is None
    assert waiting.revealed_by is None
    revealed = Clue.model_validate(
        {"id": "came-by-boat", "hidden": "true", "quote": "The thief came by boat.", "revealed_by": "P3"}
    )
    assert revealed.revealed_by == "P3"
    with pytest.raises(ValidationError, match="no document"):
        Clue.model_validate({"id": "came-by-boat", "hidden": "true", "document": "D4", "quote": "By boat."})


def test_accusation_question_correct_option_must_exist_and_options_must_be_unique() -> None:
    data = minimal_story()
    question: dict[str, Any] = {
        "id": "who",
        "prompt": "Who?",
        "options": [{"id": "ana", "text": "Ana"}, {"id": "tom", "text": "Tom"}],
        "correct": "zoe",
        "points": "40",
        "proven_by": ["flour"],
    }
    data["deduction"] = {"culprit": "ana-ruiz", "questions": [question], "exclusions": []}
    data["characters"][0]["is_culprit"] = "true"
    with pytest.raises(ValidationError, match="zoe"):
        Story.model_validate(data)
    question["correct"] = "ana"
    question["options"] = [{"id": "ana", "text": "Ana"}, {"id": "ana", "text": "Again"}]
    with pytest.raises(ValidationError, match="twice"):
        Story.model_validate(data)


def test_timeline_events_need_valid_ordered_times() -> None:
    data = minimal_story()
    data["timeline"] = [
        {"id": "storm", "start": "1923-10-02 21:00", "end": "1923-10-02 20:00", "description": "Storm."}
    ]
    with pytest.raises(ValidationError, match="end"):
        Story.model_validate(data)
    data["timeline"][0]["end"] = "1923-10-02 23:30"
    data["timeline"][0]["start"] = "02/10/1923"
    with pytest.raises(ValidationError, match="YYYY-MM-DD"):
        Story.model_validate(data)
    data["timeline"][0]["start"] = "1923-10-02"
    story = Story.model_validate(data)
    assert story.timeline[0].start_time.hour == 0
    assert story.timeline[0].end_time is not None
    assert story.timeline[0].end_time.minute == 30


def test_a_timeline_event_without_end_has_no_end_time() -> None:
    data = minimal_story()
    data["timeline"] = [{"id": "storm", "start": "1923-10-02 21:00", "description": "Storm."}]
    assert Story.model_validate(data).timeline[0].end_time is None


def test_a_minimal_puzzle_loads() -> None:
    puzzle = Puzzle.model_validate(minimal_puzzle())
    assert puzzle.params == {"shift": "3"}
    assert puzzle.hints[1].level == 2
    assert puzzle.depends_on == []
    assert puzzle.is_meta is False


def test_puzzle_hint_levels_must_count_up_from_one() -> None:
    data = minimal_puzzle()
    data["hints"][0]["level"] = "2"
    with pytest.raises(ValidationError, match="level"):
        Puzzle.model_validate(data)


def test_puzzle_clue_ids_are_unique() -> None:
    data = minimal_puzzle()
    data["clues"].append({"id": "note-shift", "document": "D2", "quote": "again"})
    with pytest.raises(ValidationError, match="note-shift"):
        Puzzle.model_validate(data)


def test_puzzle_choice_answers_need_choices_that_include_the_answer() -> None:
    data = minimal_puzzle()
    data["answer_format"] = {"kind": "choice", "label": "a suspect", "choices": ["Tom", "Ana"]}
    with pytest.raises(ValidationError, match="choices"):
        Puzzle.model_validate(data)
    data["answer"] = "Ana"
    assert Puzzle.model_validate(data).answer_format.choices == ["Tom", "Ana"]


def test_puzzle_ids_follow_the_patterns() -> None:
    data = minimal_puzzle() | {"id": "p1"}
    with pytest.raises(ValidationError, match="id"):
        Puzzle.model_validate(data)
    data = minimal_puzzle() | {"stage": "Z"}
    with pytest.raises(ValidationError, match="stage"):
        Puzzle.model_validate(data)


def test_document_meta_defaults() -> None:
    meta = DocumentMeta.model_validate(
        {"format_version": "1", "id": "D1", "kind": "letter", "stage": "A", "title": "A letter"}
    )
    assert meta.puzzle is None
    assert meta.print.cut is False
    assert meta.copies == 1
    assert meta.fields == {}


def test_flow_first_stage_opens_at_start_and_ids_are_unique() -> None:
    flow_data: dict[str, Any] = {
        "format_version": "1",
        "structure": "linear",
        "stages": [
            {"id": "A", "label": "The desk", "opens_with": "start"},
            {"id": "B", "label": "The attic", "opens_with": "P2"},
        ],
        "final_puzzle": "P5",
        "accusation": "true",
    }
    flow = Flow.model_validate(flow_data)
    assert flow.accusation is True
    flow_data["stages"][0]["opens_with"] = "P1"
    with pytest.raises(ValidationError, match="start"):
        Flow.model_validate(flow_data)
    flow_data["stages"][0]["opens_with"] = "start"
    flow_data["stages"][1]["opens_with"] = "start"
    with pytest.raises(ValidationError, match="start"):
        Flow.model_validate(flow_data)
    flow_data["stages"][1] = {"id": "A", "label": "Again", "opens_with": "P2"}
    with pytest.raises(ValidationError, match="twice"):
        Flow.model_validate(flow_data)


def test_story_visual_style_is_optional_and_limited_to_known_styles() -> None:
    assert Story.model_validate(minimal_story()).visual_style is None
    assert Story.model_validate(minimal_story() | {"visual_style": "noir"}).visual_style == "noir"
    with pytest.raises(ValidationError, match="visual_style"):
        Story.model_validate(minimal_story() | {"visual_style": "auto"})


def test_puzzle_decoys_default_to_empty() -> None:
    assert Puzzle.model_validate(minimal_puzzle()).decoys == []
    assert Puzzle.model_validate(minimal_puzzle() | {"decoys": ["Mill Pond"]}).decoys == ["Mill Pond"]
