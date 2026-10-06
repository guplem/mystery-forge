from test_render_support import golden_game, with_story

from mystery_forge.game import Game
from mystery_forge.render.solutions import (
    Citation,
    EpiloguesPage,
    SectionPage,
    SolutionPage,
    citations,
    solution_sheets,
)
from mystery_forge.spec.models import RevealStep


def test_the_solutions_have_a_cover_one_page_per_puzzle_and_the_truth() -> None:
    sheets = solution_sheets(golden_game())
    assert [sheet.role for sheet in sheets] == [
        "warning",
        "solution",
        "solution",
        "solution",
        "deduction",
        "truth",
        "epilogues",
    ]
    first = sheets[1].content
    assert isinstance(first, SolutionPage)
    assert (first.code, first.answer) == ("A1", "boathouse")
    assert first.steps[0].citations == [
        Citation(document="The keeper's logbook", quote="like the tide, my code goes back three steps")
    ]
    third = sheets[3].content
    assert isinstance(third, SolutionPage)
    assert third.accepted == ["the low tide", "at low tide"]


def test_citations_skip_an_unknown_clue() -> None:
    assert citations(golden_game(), ["nope", "felix-debt"]) == [
        Citation(document="Two papers from the box", quote="Mr Ward still owes me forty pounds for the brass sextant")
    ]


def test_the_deduction_page_explains_answers_then_exclusions() -> None:
    page = solution_sheets(golden_game())[4].content
    assert isinstance(page, SectionPage)
    assert [item.heading for item in page.items] == [
        "Who took the great lens?",
        "Why did the thief take it?",
        "Ana Ruiz",
        "Maud Price",
    ]
    assert page.items[0].text == "Felix Ward, the boatman"
    assert page.items[0].points == 50
    assert page.subtitle_before == {2: "exclusions"}


def test_the_truth_page_holds_the_truth_and_the_reveal() -> None:
    page = solution_sheets(golden_game())[5].content
    assert isinstance(page, SectionPage)
    assert page.first and page.intro == golden_game().story.truth
    assert page.subtitle_before == {0: "reveal"}
    assert len(page.items) == len(golden_game().story.reveal)


def test_epilogues_go_from_the_best_ending_down() -> None:
    page = solution_sheets(golden_game())[-1].content
    assert isinstance(page, EpiloguesPage)
    assert [item.min_score_percent for item in page.epilogues] == [75, 40, 0]


def test_a_story_without_deduction_or_reveal_skips_those_parts() -> None:
    game = with_story(golden_game(), deduction=None, reveal=[])
    sheets = solution_sheets(game)
    assert "deduction" not in [sheet.role for sheet in sheets]
    truth = next(sheet.content for sheet in sheets if sheet.role == "truth")
    assert isinstance(truth, SectionPage)
    assert truth.items == [] and truth.subtitle_before == {}


def test_a_long_reveal_spreads_over_several_pages() -> None:
    steps = [RevealStep(text="A long statement. " * 20, clues=["wet-boots"]) for _ in range(12)]
    game: Game = with_story(golden_game(), reveal=steps)
    truth_pages = [sheet.content for sheet in solution_sheets(game) if sheet.role == "truth"]
    assert len(truth_pages) > 1
    assert all(isinstance(page, SectionPage) for page in truth_pages)
    first, second = truth_pages[0], truth_pages[1]
    assert isinstance(first, SectionPage) and isinstance(second, SectionPage)
    assert first.intro and not second.intro
    assert first.subtitle_before == {0: "reveal"} and second.subtitle_before == {}
