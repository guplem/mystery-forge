from pathlib import Path

from mystery_forge.panel.models import AccusationChoice, Evidence, SolverResult, SolverStatus
from mystery_forge.panel.packets import STORY_ONLY_STAGE
from mystery_forge.panel.plain_clues import build_plain_clue_packet, judge_plain_clue_test
from mystery_forge.spec.loader import load_required_model
from mystery_forge.spec.models import Story

GOLDEN_SOURCE: Path = Path(__file__).parent / "fixtures" / "golden" / "source"


def golden_story() -> Story:
    story = load_required_model(GOLDEN_SOURCE, "story.yaml", Story, [])
    assert story is not None
    return story


def choice(option: str, quote: str) -> AccusationChoice:
    return AccusationChoice(question="who", option=option, evidence=[Evidence(document="D4", quote=quote)])


def solver(number: int, chosen: AccusationChoice, status: SolverStatus = "done") -> SolverResult:
    return SolverResult(solver=f"S{number}", stage=STORY_ONLY_STAGE, accusation=[chosen], status=status)


def test_the_packet_holds_the_plain_clues_and_the_questions_but_no_hidden_clue_or_secret() -> None:
    story = golden_story()
    packet = build_plain_clue_packet(story)
    assert packet is not None
    assert (packet.stage, packet.codes, packet.questions) == (STORY_ONLY_STAGE, [], ["who", "why"])
    assert "## Document D4\n\n> wet boot prints on the lamp room stairs, too big for Ana" in packet.text
    assert "Felix Ward (" in packet.text
    for clue in story.clues:
        assert (clue.quote in packet.text) is not clue.hidden
    assert not any(character.secret and character.secret in packet.text for character in story.characters)
    assert "- who: " in packet.text and "  - felix: " in packet.text


def test_a_story_without_an_accusation_has_no_packet() -> None:
    packet = build_plain_clue_packet(golden_story())
    assert packet is not None
    story = golden_story().model_copy(update={"deduction": None})
    assert build_plain_clue_packet(story) is None
    assert judge_plain_clue_test(story, packet, []) == []


def test_solvers_that_prove_the_culprit_from_plain_clues_fail_the_question() -> None:
    story = golden_story()
    packet = build_plain_clue_packet(story)
    assert packet is not None
    proof = choice("felix", "wet boot prints on the lamp room stairs, too big for Ana")
    verdicts = judge_plain_clue_test(story, packet, [solver(1, proof), solver(2, proof), solver(3, proof)])
    assert [(verdict.code, verdict.verdict) for verdict in verdicts] == [("who", "puzzles_not_needed"), ("why", "pass")]


def test_guesses_without_a_real_quote_and_failed_solvers_do_not_count() -> None:
    story = golden_story()
    packet = build_plain_clue_packet(story)
    assert packet is not None
    guess = choice("felix", "Felix confessed everything.")
    proof = choice("felix", "wet boot prints on the lamp room stairs, too big for Ana")
    guessed = judge_plain_clue_test(story, packet, [solver(1, guess), solver(2, guess), solver(3, proof)])
    assert guessed[0].verdict == "pass"
    too_few = judge_plain_clue_test(story, packet, [solver(1, proof), solver(2, proof), solver(3, proof, "failed")])
    assert too_few[0].verdict == "insufficient_solvers"
