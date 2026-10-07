from test_render_support import golden_game, with_story

from mystery_forge.game import Game
from mystery_forge.render.layout import page_budget
from mystery_forge.render.sheets import Sheet
from mystery_forge.render.solutions import (
    HEADER_MM,
    SOLUTIONS_GROUP,
    Citation,
    Explained,
    SectionPage,
    SolutionPage,
    citations,
    fit_item,
    item_height,
    solution_sheets,
)
from mystery_forge.spec.models import Clue, Epilogue, RevealStep, SolutionStep


def sections(sheets: list[Sheet], role: str) -> list[SectionPage]:
    pages = [sheet.content for sheet in sheets if sheet.role == role]
    assert all(isinstance(page, SectionPage) for page in pages)
    return pages  # type: ignore[return-value]


def solution_pages(sheets: list[Sheet]) -> list[SolutionPage]:
    return [sheet.content for sheet in sheets if isinstance(sheet.content, SolutionPage)]


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
    assert [sheet.group for sheet in sheets] == [None, *[SOLUTIONS_GROUP] * 3, "deduction", "truth", "epilogues"]
    first = solution_pages(sheets)[0]
    assert (first.code, first.answer, first.first, first.start) == ("A1", "boathouse", True, 1)
    assert first.steps[0].citations == [
        Citation(document="The keeper's logbook", quote="like the tide, my code goes back three steps")
    ]
    assert solution_pages(sheets)[2].accepted == ["the low tide", "at low tide"]


def test_citations_skip_an_unknown_clue() -> None:
    assert citations(golden_game(), ["nope", "felix-debt"]) == [
        Citation(document="Two papers from the box", quote="Mr Ward still owes me forty pounds for the brass sextant")
    ]


def test_a_hidden_clue_names_the_puzzle_that_reveals_it() -> None:
    game = golden_game()
    hidden = Clue(id="keys-hidden", quote="Tom hid the spare keys in the boathouse.", hidden=True, revealed_by="P1")
    unplanned = Clue(id="keys-later", quote="The keys are gone.", hidden=True)
    game = with_story(game, clues=[*game.story.clues, hidden, unplanned])
    assert citations(game, ["keys-hidden", "keys-later"]) == [
        Citation(document="Revealed by puzzle A1", quote="Tom hid the spare keys in the boathouse."),
        Citation(document="Revealed by puzzle ?", quote="The keys are gone."),
    ]


def test_internal_ids_in_the_solutions_print_as_codes_and_titles() -> None:
    game = golden_game()
    puzzles = list(game.puzzles)
    steps = [SolutionStep(text="Use the answer of P2 and the receipt D3.", uses=[])]
    puzzles[0] = puzzles[0].model_copy(update={"source": puzzles[0].source.model_copy(update={"solution": steps})})
    game = with_story(game.model_copy(update={"puzzles": puzzles}), truth="P1 led to D4.")
    sheets = solution_sheets(game)
    assert solution_pages(sheets)[0].steps[0].text == "Use the answer of A2 and the receipt The supply receipt."
    assert sections(sheets, "truth")[0].items[0].text == "A1 led to Notes from the boathouse box."


def test_the_deduction_page_explains_answers_then_exclusions() -> None:
    page = sections(solution_sheets(golden_game()), "deduction")[0]
    assert page.title_key == "deduction_title"
    assert [(item.kind, item.heading) for item in page.items] == [
        ("statement", "Who took the great lens?"),
        ("statement", "Why did the thief take it?"),
        ("subtitle", "exclusions_title"),
        ("statement", "Ana Ruiz"),
        ("statement", "Maud Price"),
    ]
    assert page.items[0].text == "Felix Ward, the boatman"
    assert page.items[0].points == 50


def test_the_truth_page_holds_the_truth_then_the_reveal() -> None:
    page = sections(solution_sheets(golden_game()), "truth")[0]
    assert page.first and page.last
    assert page.items[0] == Explained(heading="", text=golden_game().story.truth, citations=[], kind="truth")
    assert page.items[1].kind == "subtitle" and page.items[1].heading == "reveal_title"
    assert len(page.items) == 2 + len(golden_game().story.reveal)


def test_epilogues_go_from_the_best_ending_down() -> None:
    page = sections(solution_sheets(golden_game()), "epilogues")[0]
    assert [(item.kind, item.points) for item in page.items] == [("epilogue", 75), ("epilogue", 40), ("epilogue", 0)]


def test_a_story_without_deduction_or_reveal_keeps_the_truth_page() -> None:
    sheets = solution_sheets(with_story(golden_game(), deduction=None, reveal=[]))
    assert "deduction" not in [sheet.role for sheet in sheets]
    assert [item.kind for item in sections(sheets, "truth")[0].items] == ["truth"]


def test_a_long_reveal_continues_on_more_pages_and_a_subtitle_never_ends_a_page() -> None:
    steps = [RevealStep(text="A long statement. " * 20, clues=["wet-boots"]) for _ in range(12)]
    game: Game = with_story(golden_game(), reveal=steps)
    pages = sections(solution_sheets(game), "truth")
    assert len(pages) > 1
    assert [(page.first, page.last) for page in (pages[0], pages[-1])] == [(True, False), (False, True)]
    assert all(page.items[-1].kind != "subtitle" for page in pages)


def test_a_truth_longer_than_a_page_is_split_between_sentences() -> None:
    truth: str = "The keeper slept while the tide went out. " * 150
    pages = sections(solution_sheets(with_story(golden_game(), truth=truth)), "truth")
    parts = [item for page in pages for item in page.items if item.kind == "truth"]
    assert len(parts) > 1
    assert [part.continued for part in parts] == [False] + [True] * (len(parts) - 1)
    assert " ".join(part.text for part in parts) == truth.strip()


def test_a_puzzle_with_many_steps_continues_with_the_step_numbers() -> None:
    game = golden_game()
    puzzles = list(game.puzzles)
    steps = [
        SolutionStep(text=f"Step {number}. " + "Read the logbook again. " * 12, uses=["three-back"])
        for number in range(14)
    ]
    puzzles[0] = puzzles[0].model_copy(update={"source": puzzles[0].source.model_copy(update={"solution": steps})})
    pages = [
        page
        for page in solution_pages(solution_sheets(game.model_copy(update={"puzzles": puzzles})))
        if page.code == "A1"
    ]
    assert len(pages) > 1
    assert [page.first for page in pages] == [True] + [False] * (len(pages) - 1)
    assert pages[1].start == 1 + len(pages[0].steps)
    assert sum(len(page.steps) for page in pages) == 14


def test_a_tighter_level_spreads_a_section_over_more_pages() -> None:
    epilogues = [
        Epilogue(id=f"end-{number}", min_score_percent=number * 10, title=f"End {number}", text="It ends. " * 40)
        for number in range(8)
    ]
    game = with_story(golden_game(), epilogues=epilogues)
    loose = sections(solution_sheets(game), "epilogues")
    tight = sections(solution_sheets(game, {"epilogues": 3}), "epilogues")
    assert len(tight) > len(loose)


def test_fit_item_keeps_the_heading_first_and_the_citations_last() -> None:
    item = Explained(heading="Who?", text="Felix took it. " * 400, citations=[Citation("D1", "a quote")])
    budget: float = page_budget("A4", HEADER_MM, 0)
    parts = fit_item(item, budget)
    assert len(parts) > 1
    assert parts[0].heading == "Who?" and parts[1].heading == ""
    assert parts[-1].citations == item.citations and parts[0].citations == []
    assert all(item_height(part) <= budget for part in parts)
    assert fit_item(Explained(heading="", text="Short.", citations=[]), budget) == [
        Explained(heading="", text="Short.", citations=[])
    ]


def test_a_deduction_without_exclusions_has_no_exclusions_subtitle() -> None:
    deduction = golden_game().story.deduction
    assert deduction is not None
    game = with_story(golden_game(), deduction=deduction.model_copy(update={"exclusions": []}))
    page = sections(solution_sheets(game), "deduction")[0]
    assert [item.kind for item in page.items] == ["statement", "statement"]
