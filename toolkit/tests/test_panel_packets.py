import hashlib
import shutil
from pathlib import Path

import pytest
from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.assemble import assemble_game
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.panel.packets import (
    STORY_ONLY_INSTRUCTIONS,
    STORY_ONLY_STAGE,
    available_documents,
    build_guesser_packet,
    build_panel_packets,
    build_stage_packets,
    build_story_only_packet,
    canaries,
    stage_index,
)


@pytest.fixture(scope="module")
def golden_game(tmp_path_factory: pytest.TempPathFactory) -> Game:
    game_dir: Path = tmp_path_factory.mktemp("golden")
    shutil.copytree(GOLDEN_GAME / "source", game_dir / "source")
    game = assemble_game(game_dir, FAKE_IMPLEMENTATIONS).game
    assert game is not None
    return game


def without_deduction(game: Game) -> Game:
    return game.model_copy(update={"story": game.story.model_copy(update={"deduction": None})})


def test_there_is_one_packet_per_stage_in_flow_order(golden_game: Game) -> None:
    packets = build_stage_packets(golden_game)
    assert [packet.stage for packet in packets] == ["A", "B"]
    assert [packet.codes for packet in packets] == [["A1", "A2"], ["B1"]]
    assert packets[0].questions == []
    assert packets[1].questions == ["who", "why"]
    for packet in packets:
        assert packet.sha256 == hashlib.sha256(packet.text.encode()).hexdigest()


def test_a_packet_starts_with_a_neutral_player_instruction(golden_game: Game) -> None:
    text = build_stage_packets(golden_game)[0].text
    assert text.startswith("# The Lens of Gull Rock\n\nYou are a player of a printed mystery game.")
    assert golden_game.story.intro in text


def test_a_packet_holds_the_documents_available_at_its_stage(golden_game: Game) -> None:
    first, second = build_stage_packets(golden_game)
    assert "## The keeper's logbook (Notebook page)" in first.text
    assert "## The supply receipt (Receipt)" in first.text
    assert "Notes from the boathouse box" not in first.text
    assert "## Notes from the boathouse box (Police report)" in second.text
    assert "CIPHER<P1>" in first.text
    for document in golden_game.documents:
        assert document.text in second.text
    assert second.text.index("(Letter)") < second.text.index("(Notebook page)") < second.text.index("(Police report)")


def test_documents_follow_the_stage_then_the_order_then_the_number(golden_game: Game) -> None:
    reordered: list[AssembledDocument] = [
        document.model_copy(update={"meta": document.meta.model_copy(update={"order": 1})})
        if document.meta.id == "D1"
        else document
        for document in reversed(golden_game.documents)
    ]
    game = golden_game.model_copy(update={"documents": reordered})
    assert [document.meta.id for document in available_documents(game, "A")] == ["D2", "D3", "D1"]
    assert [document.meta.id for document in available_documents(game, "B")] == ["D2", "D3", "D1", "D4", "D5"]


def test_a_later_packet_lists_the_answers_of_earlier_stages_and_the_opened_envelopes(golden_game: Game) -> None:
    first, second = build_stage_packets(golden_game)
    assert "# Answers you already found\n\nNone yet." in first.text
    assert "- A1: boathouse\n- A2: 0726" in second.text
    assert "Envelope B: Inside the boathouse box you find the boatman's papers." in second.text
    assert "Envelope B" not in first.text


def test_the_puzzles_to_solve_show_the_format_and_the_attached_documents(golden_game: Game) -> None:
    first, second = build_stage_packets(golden_game)
    assert "- A1: The keeper's coded line\n  Answer format: one word (9 characters)" in first.text
    assert "  Its material is in: The keeper's logbook" in first.text
    assert "- B1: How did the thief reach the rock?\n  Answer format: two words\n" in second.text
    assert "  Its material is in: Notes from the boathouse box" in second.text


def test_a_choice_puzzle_shows_its_choices_and_a_puzzle_without_documents_says_so(golden_game: Game) -> None:
    puzzle = golden_game.puzzles[2]
    answer_format = puzzle.source.answer_format.model_copy(update={"kind": "choice", "choices": ["low tide", "dusk"]})
    choice_puzzle = puzzle.model_copy(
        update={"source": puzzle.source.model_copy(update={"answer_format": answer_format})}
    )
    documents = [document for document in golden_game.documents if document.meta.puzzle != "P3"]
    game = golden_game.model_copy(update={"puzzles": [*golden_game.puzzles[:2], choice_puzzle], "documents": documents})
    text = build_stage_packets(game)[1].text
    assert "  Choices: low tide | dusk" in text
    assert "  Its material is in: no document of its own" in text


def test_only_the_last_stage_shows_the_final_accusation(golden_game: Game) -> None:
    first, second = build_stage_packets(golden_game)
    assert "# Final accusation" not in first.text
    assert "- who: Who took the great lens?\n  - ana: Ana Ruiz, the cook" in second.text
    assert "  - debt: To pay a debt" in second.text
    no_deduction = build_stage_packets(without_deduction(golden_game))
    assert "# Final accusation" not in no_deduction[1].text
    assert no_deduction[1].questions == []


def test_the_golden_packets_hold_no_secret(golden_game: Game) -> None:
    secrets: list[str] = [golden_game.story.truth, *(epilogue.text for epilogue in golden_game.story.epilogues)]
    secrets += [character.secret for character in golden_game.story.characters if character.secret]
    secrets += [step.text for step in golden_game.story.reveal]
    for puzzle in golden_game.puzzles:
        source = puzzle.source
        secrets += [source.canary, source.mechanic, source.in_world_reason, source.reveals, source.difficulty]
        secrets += [hint.text for hint in source.hints] + [step.text for step in source.solution]
        secrets += [near_miss.answer for near_miss in source.near_misses] + list(source.decoys)
    for packet in build_stage_packets(golden_game):
        lowered: str = packet.text.casefold()
        for secret in secrets:
            assert secret.casefold() not in lowered, secret
        documents: list[AssembledDocument] = available_documents(golden_game, packet.stage)
        for puzzle in golden_game.puzzles:
            if puzzle.source.stage != packet.stage:
                continue
            for answer in (puzzle.source.answer, *puzzle.source.accepted):
                in_documents: int = sum(document.text.casefold().count(answer.casefold()) for document in documents)
                assert lowered.count(answer.casefold()) == in_documents, answer


def test_the_guesser_packet_holds_only_the_premise_and_the_formats(golden_game: Game) -> None:
    packet = build_guesser_packet(golden_game)
    assert packet.codes == ["A1", "A2", "B1"]
    assert packet.sha256 == hashlib.sha256(packet.text.encode()).hexdigest()
    assert golden_game.story.premise in packet.text
    assert golden_game.story.tagline in packet.text
    assert "- A2: a 4-digit code (4 characters)" in packet.text
    assert "logbook" not in packet.text
    assert "boathouse" not in packet.text


def test_canaries_map_each_code_to_its_canary(golden_game: Game) -> None:
    assert canaries(golden_game) == {"A1": "canary-golden-p1", "A2": "canary-golden-p2", "B1": "canary-golden-p3"}


def test_an_unknown_stage_sorts_after_every_flow_stage(golden_game: Game) -> None:
    assert stage_index(golden_game, "A") == 0
    assert stage_index(golden_game, "Z") == len(golden_game.flow.stages)
    stray = golden_game.puzzles[0].model_copy(
        update={"source": golden_game.puzzles[0].source.model_copy(update={"stage": "Z"})}
    )
    game = golden_game.model_copy(update={"puzzles": [stray, *golden_game.puzzles[1:]]})
    assert build_stage_packets(game)[0].codes == ["A2"]


def test_a_document_shows_its_printed_header_fields(golden_game: Game) -> None:
    first, _ = build_stage_packets(golden_game)
    letter_start = first.text.index("(Letter)")
    letter = first.text[letter_start : first.text.index("##", letter_start)]
    assert "sender: Harbour Master E. Lowe" in letter
    assert "date: 15 March 1931" in letter


def test_the_story_only_packet_holds_the_plain_documents_and_the_accusation_only(golden_game: Game) -> None:
    packet = build_story_only_packet(golden_game)
    assert packet is not None
    assert (packet.stage, packet.codes, packet.questions) == (STORY_ONLY_STAGE, [], ["who", "why"])
    assert packet.sha256 == hashlib.sha256(packet.text.encode()).hexdigest()
    assert packet.text.startswith(f"# The Lens of Gull Rock\n\n{STORY_ONLY_INSTRUCTIONS}")
    assert "## A letter from the harbour master (Letter)" in packet.text
    assert "## Two papers from the box (Generic document)" in packet.text
    assert "## The keeper's logbook" not in packet.text
    assert "## Notes from the boathouse box" not in packet.text
    assert "Inside the boathouse box you find the boatman's papers." in packet.text
    assert "# Answers you already found" not in packet.text
    assert "# Puzzles to solve now" not in packet.text
    assert "- who: Who took the great lens?" in packet.text


def test_the_story_only_packet_asks_only_the_questions_that_a_puzzle_proves(golden_game: Game) -> None:
    assert golden_game.story.deduction is not None
    who, why = golden_game.story.deduction.questions
    plain_why = why.model_copy(update={"proven_by": ["felix-debt"]})
    deduction = golden_game.story.deduction.model_copy(update={"questions": [who, plain_why]})
    game = golden_game.model_copy(update={"story": golden_game.story.model_copy(update={"deduction": deduction})})
    packet = build_story_only_packet(game)
    assert packet is not None
    assert packet.questions == ["who"]
    assert "- why:" not in packet.text
    plain_who = who.model_copy(update={"proven_by": ["felix-debt"]})
    no_proof = deduction.model_copy(update={"questions": [plain_who, plain_why]})
    assert (
        build_story_only_packet(
            game.model_copy(update={"story": game.story.model_copy(update={"deduction": no_proof})})
        )
        is None
    )
    assert build_story_only_packet(without_deduction(golden_game)) is None


def test_the_panel_packets_add_the_story_only_packet_after_the_stages(golden_game: Game) -> None:
    assert [packet.stage for packet in build_panel_packets(golden_game)] == ["A", "B", STORY_ONLY_STAGE]
    assert [packet.stage for packet in build_panel_packets(without_deduction(golden_game))] == ["A", "B"]
