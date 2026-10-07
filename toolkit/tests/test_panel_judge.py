import json
import shutil
from pathlib import Path

import pytest
from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.assemble import assemble_game
from mystery_forge.checks.ledger import normalize_quote_text
from mystery_forge.game import Game
from mystery_forge.panel.judge import (
    SUMMARY_LIMIT_BYTES,
    evidence_verified,
    judge_panel,
    report_summary,
    required_solves,
)
from mystery_forge.panel.models import (
    AccusationChoice,
    Alternative,
    Candidate,
    Evidence,
    Guess,
    GuesserResult,
    ItemVerdict,
    PanelReport,
    SolverAnswer,
    SolverResult,
)
from mystery_forge.panel.packets import STORY_ONLY_STAGE, StagePacket, build_panel_packets, build_stage_packets
from mystery_forge.spec.models import Difficulty

GOOD_ANSWERS: dict[str, tuple[str, str]] = {
    "A1": ("boathouse", "like the tide, my code goes back three steps"),
    "A2": ("0726", "Lamp oil: 7 barrels"),
    "B1": ("low tide", "Low tide: 1:50 in the night"),
}
DEBT_QUOTE: str = "Mr Ward still owes me forty pounds for the brass sextant"


@pytest.fixture(scope="module")
def golden_game(tmp_path_factory: pytest.TempPathFactory) -> Game:
    game_dir: Path = tmp_path_factory.mktemp("golden")
    shutil.copytree(GOLDEN_GAME / "source", game_dir / "source")
    game = assemble_game(game_dir, FAKE_IMPLEMENTATIONS).game
    assert game is not None
    return game


@pytest.fixture(scope="module")
def packets(golden_game: Game) -> list[StagePacket]:
    return build_stage_packets(golden_game)


def evidence(*quotes: str) -> list[Evidence]:
    return [Evidence(document="The keeper's logbook", quote=quote) for quote in quotes]


def good_answer(code: str) -> SolverAnswer:
    text, quote = GOOD_ANSWERS[code]
    return SolverAnswer(code=code, answer=text, evidence=evidence(quote), reasoning="It fits.")


def good_accusation() -> list[AccusationChoice]:
    return [
        AccusationChoice(question="who", option="felix", evidence=evidence(DEBT_QUOTE)),
        AccusationChoice(question="why", option="debt", evidence=evidence(DEBT_QUOTE)),
    ]


def stage_a(name: str, *answers: SolverAnswer) -> SolverResult:
    return SolverResult(solver=name, stage="A", answers=list(answers))


def stage_b(name: str, answer: SolverAnswer, accusation: list[AccusationChoice] | None = None) -> SolverResult:
    return SolverResult(
        solver=name, stage="B", answers=[answer], accusation=good_accusation() if accusation is None else accusation
    )


def full_panel(stage_b_results: list[SolverResult] | None = None) -> list[SolverResult]:
    results: list[SolverResult] = [stage_a(f"a{index}", good_answer("A1"), good_answer("A2")) for index in range(5)]
    if stage_b_results is None:
        stage_b_results = [stage_b(f"b{index}", good_answer("B1")) for index in range(5)]
    return results + stage_b_results


def verdict_of(report: PanelReport, code: str) -> ItemVerdict:
    return next(item for item in [*report.puzzles, *report.questions] if item.code == code)


@pytest.mark.parametrize(
    ("difficulty", "solvers", "required"),
    [
        ("easy", 5, 3),
        ("medium", 6, 3),
        ("hard", 5, 2),
        ("expert", 5, 2),
        ("easy", 4, 2),
        ("medium", 3, 2),
        ("hard", 3, 1),
        ("expert", 4, 1),
        ("easy", 2, None),
        ("hard", 0, None),
    ],
)
def test_the_required_solves_follow_the_difficulty_and_the_panel_size(
    difficulty: Difficulty, solvers: int, required: int | None
) -> None:
    assert required_solves(difficulty, solvers) == required


def test_evidence_is_verified_only_when_every_quote_is_in_the_packet() -> None:
    packet_text: str = normalize_quote_text("He said: it's late - very late.\nThe end.")
    curly: str = f"it{chr(0x2019)}s late {chr(0x2013)} very"
    assert evidence_verified(evidence(curly, "late.  The end"), packet_text)
    assert evidence_verified(evidence('"The end."'), packet_text)
    assert not evidence_verified(evidence("it's late", "not here"), packet_text)
    assert not evidence_verified([], packet_text)
    assert not evidence_verified(evidence('""'), packet_text)


def test_a_full_correct_panel_passes(golden_game: Game, packets: list[StagePacket]) -> None:
    report = judge_panel(golden_game, packets, full_panel(), GuesserResult(guesses=[Guess(code="A1", answer="lamp")]))
    assert report.ok
    assert [item.code for item in report.puzzles] == ["A1", "A2", "B1"]
    assert [item.code for item in report.questions] == ["who", "why"]
    first = report.puzzles[0]
    assert (first.verdict, first.solvers, first.required, first.solves_verified, first.guesses) == ("pass", 5, 3, 5, 0)
    assert first.wrong == [] and first.alternatives == [] and not first.guessable
    assert report.invalid_solvers == []
    assert report_summary(report) == {"ok": True, "verdicts": {"pass": 5}, "invalid_solvers": 0, "failing": []}


def test_a_correct_answer_without_verified_evidence_is_a_guess(golden_game: Game, packets: list[StagePacket]) -> None:
    unproven = SolverAnswer(code="B1", answer="Low tide!", evidence=evidence("Low tide: 1:50 in the morning"))
    later_document = SolverAnswer(code="A2", answer="0726", evidence=evidence("Low tide: 1:50 in the night"))
    results = full_panel([stage_b(f"b{index}", unproven) for index in range(3)])
    results[0] = stage_a("a0", good_answer("A1"), later_document)
    report = judge_panel(golden_game, packets, results, None)
    tide = verdict_of(report, "B1")
    assert (tide.verdict, tide.solves_verified, tide.guesses, tide.required) == ("too_hard", 0, 3, 2)
    assert tide.notes[0] == "b0: correct but without verified evidence"
    lock = verdict_of(report, "A2")
    assert (lock.verdict, lock.solves_verified, lock.guesses) == ("pass", 4, 1)
    assert not report.ok


def test_too_hard_lists_what_the_solvers_did(golden_game: Game, packets: list[StagePacket]) -> None:
    stuck = SolverAnswer(code="A1", stuck=True, reasoning="The code makes no sense.")
    results = full_panel()
    results[0] = stage_a("a0", stuck, good_answer("A2"))
    results[1] = stage_a("a1", SolverAnswer(code="A1", answer="lighthouse", reasoning="A guess."), good_answer("A2"))
    results[2] = stage_a("a2", good_answer("A2"))
    results[3] = stage_a("a3", good_answer("A2"))
    report = judge_panel(golden_game, packets, results, None)
    item = verdict_of(report, "A1")
    assert (item.verdict, item.solves_verified, item.required) == ("too_hard", 1, 3)
    assert item.notes == [
        "a0: stuck: The code makes no sense.",
        "a1: answered 'lighthouse': A guess.",
        "a2: stuck: no answer given",
        "a3: stuck: no answer given",
    ]
    assert item.wrong[0].answer == "lighthouse" and item.wrong[0].count == 1
    assert item.alternatives == []
    summary = report_summary(report)
    assert summary["failing"] == [{"code": "A1", "reason": "too hard: 1 verified solves of 5, needs 3"}]


def test_too_few_valid_solvers_give_no_verdict(golden_game: Game, packets: list[StagePacket]) -> None:
    results = [stage_a("a0", good_answer("A1"), good_answer("A2")), stage_b("b0", good_answer("B1"))]
    report = judge_panel(golden_game, packets, results, None)
    item = verdict_of(report, "A1")
    assert (item.verdict, item.solvers, item.required) == ("insufficient_solvers", 1, None)
    assert verdict_of(report, "who").verdict == "insufficient_solvers"
    assert report_summary(report)["failing"][0] == {
        "code": "A1",
        "reason": "too few valid solvers: 1, the panel needs 3",
    }


def test_invalid_solvers_do_not_count(golden_game: Game, packets: list[StagePacket]) -> None:
    cheater = SolverAnswer(code="A1", answer="boathouse", evidence=evidence("x"), reasoning="See CANARY-golden-p2.")
    results = full_panel()
    results[0] = stage_a("a0", cheater, good_answer("A2"))
    results[1] = SolverResult(solver="a1", stage="A", status="failed")
    results.append(SolverResult(solver="z9", stage="Z", answers=[good_answer("A1")]))
    report = judge_panel(golden_game, packets, results, None)
    assert [(invalid.solver, invalid.stage) for invalid in report.invalid_solvers] == [
        ("a0", "A"),
        ("a1", "A"),
        ("z9", "Z"),
    ]
    assert "A2" in report.invalid_solvers[0].reason
    assert report.invalid_solvers[1].reason == "The solver failed."
    assert report.invalid_solvers[2].reason == "No packet exists for stage Z."
    item = verdict_of(report, "A1")
    assert (item.verdict, item.solvers, item.required, item.solves_verified) == ("pass", 3, 2, 3)
    assert report_summary(report)["invalid_solvers"] == 3


def test_answers_for_codes_outside_the_packet_are_ignored(golden_game: Game, packets: list[StagePacket]) -> None:
    results = full_panel()
    results[0] = stage_a("a0", good_answer("A1"), good_answer("A2"), good_answer("B1"), good_answer("A1"))
    report = judge_panel(golden_game, packets, results, None)
    assert verdict_of(report, "B1").solvers == 5
    assert verdict_of(report, "A1").solves_verified == 5


def test_a_wrong_answer_that_two_solvers_share_makes_the_puzzle_ambiguous(
    golden_game: Game, packets: list[StagePacket]
) -> None:
    high = SolverAnswer(code="B1", answer="High tide", evidence=evidence("bogus"), reasoning="Boats float then.")
    rival = Candidate(answer="high tide", failing_clue="The table says low tide.")
    correct_with_rival = good_answer("B1").model_copy(update={"candidates": [rival]})
    results = full_panel([stage_b("b0", high), stage_b("b1", high), stage_b("b2", correct_with_rival)])
    silent_rival = good_answer("B1").model_copy(update={"candidates": [Candidate(answer="High tide")]})
    results += [stage_b("b3", silent_rival), stage_b("b4", good_answer("B1"))]
    report = judge_panel(golden_game, packets, results, None)
    item = verdict_of(report, "B1")
    assert (item.verdict, item.solves_verified) == ("ambiguous", 3)
    assert item.alternatives[0].answer == "High tide"
    assert item.alternatives[0].count == 2
    assert item.alternatives[0].notes == [
        "b0: Boats float then.",
        "b1: Boats float then.",
        "b2 rules it out: The table says low tide.",
    ]
    summary = report_summary(report)
    assert summary["failing"] == [{"code": "B1", "reason": "ambiguous: other answers fit: 'High tide' (2)"}]


def test_a_candidate_that_fits_every_clue_makes_the_puzzle_ambiguous(
    golden_game: Game, packets: list[StagePacket]
) -> None:
    fits = Candidate(answer="ebb tide", fits_all_clues=True)
    gold_fits = Candidate(answer="at low tide", fits_all_clues=True)
    verified = good_answer("B1").model_copy(update={"candidates": [fits, gold_fits, Candidate(answer=" ")]})
    unverified = SolverAnswer(code="B1", answer="low tide", candidates=[Candidate(answer="dusk", fits_all_clues=True)])
    results = full_panel([stage_b("b0", verified), stage_b("b1", unverified)])
    results += [stage_b(f"b{index}", good_answer("B1")) for index in (2, 3, 4)]
    report = judge_panel(golden_game, packets, results, None)
    item = verdict_of(report, "B1")
    assert item.verdict == "ambiguous"
    assert [(alternative.answer, alternative.count) for alternative in item.alternatives] == [("ebb tide", 1)]
    assert item.alternatives[0].notes == ["b0: fits every clue"]


def test_three_solvers_on_the_same_wrong_answer_make_the_gold_suspect(
    golden_game: Game, packets: list[StagePacket]
) -> None:
    high = SolverAnswer(code="B1", answer="high tide", evidence=evidence(GOOD_ANSWERS["B1"][1]))
    results = full_panel([stage_b(f"b{index}", high) for index in range(3)])
    results += [stage_b(f"b{index}", good_answer("B1")) for index in (3, 4)]
    report = judge_panel(golden_game, packets, results, None)
    item = verdict_of(report, "B1")
    assert item.verdict == "gold_suspect"
    assert item.notes == ["3 solvers agree on 'high tide' with verified evidence. Check the official answer first."]
    assert report_summary(report)["failing"][0]["reason"].startswith("gold suspect: 3 solvers agree on 'high tide'")


def test_a_correct_guess_marks_the_puzzle_guessable(golden_game: Game, packets: list[StagePacket]) -> None:
    guesses = [Guess(code="A1", answer="The Boathouse!"), Guess(code="Z1", answer="x"), Guess(code="A2", answer="")]
    report = judge_panel(golden_game, packets, full_panel(), GuesserResult(guesses=guesses))
    item = verdict_of(report, "A1")
    assert (item.verdict, item.guessable) == ("guessable", True)
    assert item.notes == ["The guesser found the answer without the documents."]
    assert verdict_of(report, "A2").verdict == "pass"
    assert report_summary(report)["failing"] == [
        {"code": "A1", "reason": "guessable: the guesser found it without the documents"}
    ]


def test_accusation_questions_are_judged_like_medium_puzzles(golden_game: Game, packets: list[StagePacket]) -> None:
    wrong = [
        AccusationChoice(question="who", option="Ana", evidence=evidence(DEBT_QUOTE)),
        AccusationChoice(question="why", option=" DEBT ", evidence=[]),
    ]
    results = full_panel([stage_b(f"b{index}", good_answer("B1"), wrong) for index in range(2)])
    results += [stage_b(f"b{index}", good_answer("B1")) for index in (2, 3, 4)]
    results.append(stage_b("b5", good_answer("B1"), good_accusation()[:1]))
    report = judge_panel(golden_game, packets, results, None)
    who = verdict_of(report, "who")
    assert (who.verdict, who.required, who.solves_verified) == ("ambiguous", 3, 4)
    assert who.alternatives[0].answer == "Ana"
    why = verdict_of(report, "why")
    assert (why.verdict, why.solvers, why.solves_verified, why.guesses) == ("pass", 6, 3, 2)


def test_a_game_without_a_deduction_has_no_questions(golden_game: Game) -> None:
    game = golden_game.model_copy(update={"story": golden_game.story.model_copy(update={"deduction": None})})
    report = judge_panel(game, build_stage_packets(game), full_panel(), None)
    assert report.questions == []
    assert report.ok


def test_the_summary_stays_small_with_many_failing_items() -> None:
    item = ItemVerdict(
        code="A1",
        verdict="ambiguous",
        solvers=5,
        required=4,
        solves_verified=4,
        guesses=0,
        wrong=[],
        alternatives=[],
        guessable=False,
        notes=[],
    )
    long_answer: str = "x" * 200
    ambiguous = item.model_copy(update={"alternatives": [Alternative(answer=long_answer, count=2, notes=[])] * 3})
    report = PanelReport(
        ok=False,
        puzzles=[ambiguous.model_copy(update={"code": f"C{index}"}) for index in range(300)],
        questions=[],
        invalid_solvers=[],
    )
    summary = report_summary(report)
    assert len(json.dumps(summary).encode()) <= SUMMARY_LIMIT_BYTES
    assert summary["more_failing"] == 300 - len(summary["failing"])
    assert all(len(entry["reason"]) <= 100 for entry in summary["failing"])
    assert summary["verdicts"] == {"ambiguous": 300}


def stated(code: str, aha: str = "") -> SolverAnswer:
    return good_answer(code).model_copy(update={"all_steps_stated": True, "aha": aha})


def test_a_puzzle_whose_material_states_every_step_is_trivial(golden_game: Game, packets: list[StagePacket]) -> None:
    results = full_panel()
    for index in range(3):
        results[index] = stage_a(f"a{index}", stated("A1"), stated("A2", aha="read the receipt"))
    report = judge_panel(golden_game, packets, results, None)
    lock = verdict_of(report, "A2")
    assert lock.verdict == "trivial"
    assert lock.notes == [f"a{index}: the material states every step; aha: read the receipt" for index in range(3)]
    assert verdict_of(report, "A1").verdict == "pass"
    assert not report.ok
    assert report_summary(report)["failing"] == [
        {"code": "A2", "reason": "trivial: 3 of 5 solvers say the material states every step"}
    ]


def test_trivial_needs_half_of_the_solvers_that_solved_it(golden_game: Game, packets: list[StagePacket]) -> None:
    results = full_panel()
    results[0] = stage_a("a0", good_answer("A1"), stated("A2"))
    results[1] = stage_a("a1", good_answer("A1"), stated("A2"))
    results[2] = stage_a("a2", good_answer("A1"), SolverAnswer(code="A2", stuck=True))
    assert verdict_of(judge_panel(golden_game, packets, results, None), "A2").verdict == "trivial"
    results[1] = stage_a("a1", good_answer("A1"), good_answer("A2"))
    assert verdict_of(judge_panel(golden_game, packets, results, None), "A2").verdict == "pass"
    unproven = SolverAnswer(code="A2", answer="0726", all_steps_stated=True)
    results = full_panel()
    results[0] = stage_a("a0", good_answer("A1"), unproven)
    assert verdict_of(judge_panel(golden_game, packets, results, None), "A2").verdict == "pass"


def test_trivial_comes_after_guessable_and_before_too_hard(golden_game: Game, packets: list[StagePacket]) -> None:
    results = full_panel()
    results[0] = stage_a("a0", good_answer("A1"), stated("A2"))
    for index in range(1, 5):
        results[index] = stage_a(f"a{index}", good_answer("A1"), SolverAnswer(code="A2", stuck=True))
    report = judge_panel(golden_game, packets, results, None)
    assert verdict_of(report, "A2").verdict == "trivial"
    guessed = judge_panel(golden_game, packets, results, GuesserResult(guesses=[Guess(code="A2", answer="0726")]))
    assert verdict_of(guessed, "A2").verdict == "guessable"


def story_only(name: str, *choices: AccusationChoice) -> SolverResult:
    return SolverResult(solver=name, stage=STORY_ONLY_STAGE, accusation=list(choices))


PROVEN_WHY = AccusationChoice(question="why", option="debt", evidence=evidence(DEBT_QUOTE))


def test_story_only_solvers_who_prove_a_question_make_the_puzzles_not_needed(golden_game: Game) -> None:
    panel_packets = build_panel_packets(golden_game)
    unproven_who = AccusationChoice(question="who", option="felix", evidence=[])
    results = full_panel() + [story_only(f"s{index}", unproven_who, PROVEN_WHY) for index in range(5)]
    report = judge_panel(golden_game, panel_packets, results, None)
    assert not report.ok
    assert [(item.code, item.verdict, item.solvers) for item in report.questions] == [
        ("who", "pass", 5),
        ("why", "pass", 5),
    ]
    assert [(item.code, item.verdict) for item in report.story_only] == [("who", "pass"), ("why", "puzzles_not_needed")]
    why = report.story_only[1]
    assert (why.solvers, why.required, why.solves_verified) == (5, 3, 5)
    assert report_summary(report)["failing"] == [
        {"code": "why", "reason": "puzzles not needed: 5 of 5 solvers proved it without any puzzle answer"}
    ]


def test_story_only_proofs_below_the_threshold_keep_the_puzzles_needed(golden_game: Game) -> None:
    results = full_panel() + [story_only(f"s{index}", PROVEN_WHY) for index in range(2)]
    results += [story_only(f"s{index}") for index in (2, 3, 4)]
    report = judge_panel(golden_game, build_panel_packets(golden_game), results, None)
    assert report.ok
    assert [item.verdict for item in report.story_only] == ["pass", "pass"]


def test_too_few_story_only_solvers_give_no_verdict(golden_game: Game) -> None:
    results = [*full_panel(), story_only("s0", PROVEN_WHY)]
    report = judge_panel(golden_game, build_panel_packets(golden_game), results, None)
    assert not report.ok
    assert [item.verdict for item in report.story_only] == ["insufficient_solvers", "insufficient_solvers"]


def test_without_the_story_only_packet_the_report_has_no_story_only_items(golden_game: Game) -> None:
    report = judge_panel(golden_game, build_stage_packets(golden_game), full_panel(), None)
    assert report.story_only == []


def test_the_judge_judges_only_the_items_of_the_packets_that_it_gets(golden_game: Game) -> None:
    stage_b_only = [packet for packet in build_panel_packets(golden_game) if packet.stage == "B"]
    results = [stage_b(f"b{index}", good_answer("B1")) for index in range(5)]
    report = judge_panel(golden_game, stage_b_only, results, None)
    assert [item.code for item in report.puzzles] == ["B1"]
    assert [item.code for item in report.questions] == ["who", "why"]
    assert report.story_only == []
    assert report.ok
    stage_a_only = [packet for packet in build_panel_packets(golden_game) if packet.stage == "A"]
    report = judge_panel(golden_game, stage_a_only, full_panel([]), None)
    assert [item.code for item in report.puzzles] == ["A1", "A2"]
    assert report.questions == []


def with_gap(code: str, gap: str) -> SolverAnswer:
    return good_answer(code).model_copy(update={"gaps": [gap]})


def test_a_gap_that_most_solvers_report_makes_the_puzzle_incomplete(
    golden_game: Game, packets: list[StagePacket]
) -> None:
    results = full_panel()
    for index in range(3):
        results[index] = stage_a(f"a{index}", good_answer("A1"), with_gap("A2", "No document shows the oil stamp."))
    report = judge_panel(golden_game, packets, results, None)
    lock = verdict_of(report, "A2")
    assert (lock.verdict, lock.gaps) == ("incomplete", 3)
    assert lock.notes == [f"a{index}: No document shows the oil stamp." for index in range(3)]
    assert not report.ok
    assert report_summary(report)["failing"] == [
        {"code": "A2", "reason": "incomplete: 3 of 5 solvers say a step has no support in the material"}
    ]


def test_a_gap_that_few_solvers_report_does_not_fail_the_puzzle(golden_game: Game, packets: list[StagePacket]) -> None:
    results = full_panel()
    for index in range(2):
        results[index] = stage_a(f"a{index}", good_answer("A1"), with_gap("A2", "I guessed one letter."))
    assert verdict_of(judge_panel(golden_game, packets, results, None), "A2").verdict == "pass"


def test_incomplete_comes_after_guessable_and_before_trivial(golden_game: Game, packets: list[StagePacket]) -> None:
    gapped_and_stated = with_gap("A2", "A link is missing.").model_copy(update={"all_steps_stated": True})
    results = full_panel()
    for index in range(5):
        results[index] = stage_a(f"a{index}", good_answer("A1"), gapped_and_stated)
    assert verdict_of(judge_panel(golden_game, packets, results, None), "A2").verdict == "incomplete"
    guess = GuesserResult(guesses=[Guess(code="A2", answer="0726")])
    assert verdict_of(judge_panel(golden_game, packets, results, guess), "A2").verdict == "guessable"


def test_a_kids_game_may_state_its_methods(golden_game: Game, packets: list[StagePacket]) -> None:
    """The design rules ask kids' games to state each step, so a stated method is no flaw there."""
    kids_game = golden_game.model_copy(update={"config": golden_game.config.model_copy(update={"audience": "kids"})})
    results = full_panel()
    for index in range(3):
        results[index] = stage_a(f"a{index}", stated("A1"), stated("A2", aha="read the receipt"))
    assert verdict_of(judge_panel(kids_game, packets, results, None), "A2").verdict == "pass"
