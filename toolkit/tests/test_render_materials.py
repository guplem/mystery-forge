from test_render_support import configured, golden_game, showcase_game, with_story

from mystery_forge.game import Game
from mystery_forge.mechanics.base import Artifact
from mystery_forge.render.materials import (
    AccusationContent,
    DetectiveNotesContent,
    DocumentPage,
    EnvelopeLabelsContent,
    RegisterPage,
    ResultsPage,
    StageCoverContent,
    materials_sheets,
)
from mystery_forge.render.sheets import Sheet
from mystery_forge.spec.models import AccusationOption, AccusationQuestion, Location, NearMiss, Stage


def roles(sheets: list[Sheet]) -> list[str]:
    return [sheet.role for sheet in sheets]


def document_pages(sheets: list[Sheet]) -> list[DocumentPage]:
    return [sheet.content for sheet in sheets if isinstance(sheet.content, DocumentPage)]


def test_the_golden_stack_follows_the_setup_order() -> None:
    sheets = materials_sheets(golden_game())
    assert roles(sheets) == [
        "cover",
        "envelope-labels",
        "register",
        "register-results",
        "detective-notes",
        "stage-cover",
        "document",
        "document",
        "document",
        "stage-cover",
        "document",
        "document",
        "accusation",
    ]
    assert [sheet.stage for sheet in sheets[5:]] == ["A", "A", "A", "A", "B", "B", "B", "B"]
    assert all(sheet.stage is None for sheet in sheets[:5])


def test_stage_covers_say_when_to_open_without_the_answer() -> None:
    covers = [
        sheet.content for sheet in materials_sheets(golden_game()) if isinstance(sheet.content, StageCoverContent)
    ]
    assert covers[0].envelope == "Envelope A"
    assert covers[0].open_text == "Open this envelope at the start of the game."
    assert "A1" in covers[1].open_text
    assert "boathouse" not in covers[1].open_text.lower()
    assert covers[1].stage_label == "The boathouse box"
    assert covers[1].opening_text.startswith("Inside the boathouse box")


def test_envelope_labels_show_no_stage_label() -> None:
    labels = next(
        sheet.content for sheet in materials_sheets(golden_game()) if isinstance(sheet.content, EnvelopeLabelsContent)
    )
    assert [(label.stage, label.envelope, label.open_text) for label in labels.labels] == [
        ("A", "Envelope A", "Open at the start"),
        ("B", "Envelope B", "Open only after puzzle A1"),
    ]


def test_document_pages_carry_the_puzzle_code_the_artifact_and_the_kind() -> None:
    pages = document_pages(materials_sheets(golden_game()))
    assert [page.document_id for page in pages] == ["D1", "D2", "D3", "D4", "D5"]
    assert [page.puzzle_code for page in pages] == [None, "A1", "A2", "B1", None]
    assert pages[0].kind.id == "letter"
    assert '<div class="mf-artifact" data-artifact="P1">' in pages[1].html
    assert "⟦" not in pages[1].html


def test_documents_sort_by_order_then_number_and_repeat_their_copies() -> None:
    pages = document_pages(materials_sheets(showcase_game()))
    stage_a = [page.document_id for page in pages if page.document_id != "D4" and page.document_id != "D5"]
    assert stage_a[:4] == ["D1", "D2", "D3", "D10"]
    receipts = [page for page in pages if page.kind.id == "receipt" and page.document_id == "D12"]
    assert [(page.copy_number, page.copies) for page in receipts] == [(1, 2), (2, 2)]
    briefing = [page for page in pages if page.kind.id == "case-briefing"]
    assert [(page.page_number, page.page_count) for page in briefing] == [(1, 2), (2, 2)]
    ticket = next(page for page in pages if page.kind.id == "ticket")
    assert ticket.cut and not ticket.fold
    letter = next(page for page in pages if page.document_id == "D10")
    assert letter.fold
    assert next(page for page in pages if page.kind.id == "map").note == "Keep flat"
    photo = next(page for page in pages if page.kind.id == "photo")
    assert '<figure class="mf-figure" data-image="lamp">' in photo.html


def test_an_unknown_kind_prints_as_generic() -> None:
    game = golden_game()
    documents = list(game.documents)
    documents[4] = documents[4].model_copy(update={"meta": documents[4].meta.model_copy(update={"kind": "scroll"})})
    pages = document_pages(materials_sheets(game.model_copy(update={"documents": documents})))
    assert pages[4].kind.id == "generic"


def test_optional_pages_follow_the_config_and_the_story() -> None:
    game = configured(
        golden_game(),
        {"format": "envelopes"},
        equipment={"envelopes": False},
        assistance={"paper_answer_check": False},
    )
    game = with_story(game, deduction=None)
    sheets = materials_sheets(game)
    assert "envelope-labels" not in roles(sheets)
    assert "register" not in roles(sheets)
    assert "detective-notes" not in roles(sheets)
    assert "accusation" not in roles(sheets)


def test_detective_notes_list_the_suspects_or_everyone() -> None:
    def notes(game: Game) -> DetectiveNotesContent:
        return next(
            sheet.content for sheet in materials_sheets(game) if isinstance(sheet.content, DetectiveNotesContent)
        )

    assert notes(golden_game()).suspects == ["Ana Ruiz", "Felix Ward", "Maud Price"]
    assert notes(golden_game()).locations == ["the lamp room", "the kitchen"]
    characters = [character.model_copy(update={"is_suspect": False}) for character in golden_game().story.characters]
    game = with_story(golden_game(), characters=characters, deduction=None)
    assert notes(game).suspects == ["Tom Bell", "Ana Ruiz", "Felix Ward", "Maud Price"]


def test_a_long_register_spreads_over_several_pages() -> None:
    game = golden_game()
    puzzles = list(game.puzzles)
    misses = [NearMiss(answer=f"wrong{number}", message="No. " * 40) for number in range(200)]
    puzzles[0] = puzzles[0].model_copy(update={"source": puzzles[0].source.model_copy(update={"near_misses": misses})})
    sheets = materials_sheets(game.model_copy(update={"puzzles": puzzles}))
    register_pages = [sheet.content for sheet in sheets if isinstance(sheet.content, RegisterPage)]
    result_pages = [sheet.content for sheet in sheets if isinstance(sheet.content, ResultsPage)]
    assert len(register_pages) == 2
    assert [page.first for page in register_pages] == [True, False]
    assert len(result_pages) > 2
    assert result_pages[0].first and not result_pages[1].first


def test_a_missing_artifact_still_marks_its_place() -> None:
    game = golden_game()
    puzzles = list(game.puzzles)
    puzzles[0] = puzzles[0].model_copy(update={"artifact": None})
    puzzles[1] = puzzles[1].model_copy(update={"artifact": Artifact(html="<b>lock</b>", solver_text="x")})
    pages = document_pages(materials_sheets(game.model_copy(update={"puzzles": puzzles})))
    assert 'mf-artifact-missing" data-artifact="P1"' in pages[1].html
    assert "<b>lock</b>" in pages[2].html


def notes_pages(game: Game) -> list[DetectiveNotesContent]:
    return [sheet.content for sheet in materials_sheets(game) if isinstance(sheet.content, DetectiveNotesContent)]


def test_the_notes_grid_puts_places_in_rows_and_spreads_many_places_over_pages() -> None:
    golden = notes_pages(golden_game())
    assert len(golden) == 1 and golden[0].first and golden[0].last
    places = [Location(id=f"place-{number}", name=f"Place {number}", description="x") for number in range(20)]
    characters = [
        character.model_copy(update={"id": f"person-{number}", "name": f"Person {number}", "is_suspect": True})
        for number, character in enumerate([golden_game().story.characters[1]] * 8)
    ]
    big = with_story(golden_game(), locations=places, characters=characters, deduction=None)
    pages = notes_pages(big)
    assert [location for page in pages for location in page.locations] == [place.name for place in places]
    assert all(len(page.suspects) == 8 for page in pages)
    assert (pages[0].first, pages[0].last) == (True, len(pages) == 1)
    assert pages[-1].last
    many = notes_pages(with_story(golden_game(), locations=places * 4))
    assert len(many) > 1 and many[0].locations


def test_a_tighter_notes_level_moves_places_to_later_pages() -> None:
    places = [Location(id=f"place-{number}", name=f"Place {number}", description="x") for number in range(12)]
    game = with_story(golden_game(), locations=places)
    loose = [sheet for sheet in materials_sheets(game) if sheet.role == "detective-notes"]
    tight = [sheet for sheet in materials_sheets(game, {"notes": 3}) if sheet.role == "detective-notes"]
    assert len(tight) > len(loose)
    assert {sheet.group for sheet in tight} == {"notes"}


def test_many_stages_spread_their_labels_over_several_pages() -> None:
    game = golden_game()
    stages = [
        Stage(id=letter, label=f"Part {letter}", opens_with="start" if letter == "A" else "P1") for letter in "ABCDEFGH"
    ]
    game = game.model_copy(update={"flow": game.flow.model_copy(update={"stages": stages})})
    labels = [sheet.content for sheet in materials_sheets(game) if isinstance(sheet.content, EnvelopeLabelsContent)]
    assert len(labels) == 2
    assert [label.stage for page in labels for label in page.labels] == list("ABCDEFGH")


def test_a_long_accusation_form_continues_with_its_numbers() -> None:
    options = [AccusationOption(id=f"o{number}", text=f"A rather long option number {number}") for number in range(8)]
    questions = [
        AccusationQuestion(
            id=f"q{number}",
            prompt=f"Question {number}?",
            options=options,
            correct="o1",
            points=10,
            proven_by=["wet-boots"],
        )
        for number in range(8)
    ]
    deduction = golden_game().story.deduction
    assert deduction is not None
    game = with_story(golden_game(), deduction=deduction.model_copy(update={"questions": questions}))
    pages = [sheet.content for sheet in materials_sheets(game) if isinstance(sheet.content, AccusationContent)]
    assert len(pages) > 1
    assert [page.first for page in pages] == [True] + [False] * (len(pages) - 1)
    assert [page.last for page in pages] == [False] * (len(pages) - 1) + [True]
    assert pages[1].start == 1 + len(pages[0].questions)
    assert all(page.total_points == 80 for page in pages)


def test_a_result_paragraph_taller_than_a_column_goes_on_in_a_second_part() -> None:
    game = golden_game()
    puzzles = list(game.puzzles)
    reveals: str = "The keeper hid the keys in the boathouse under a loose board. " * 60
    puzzles[0] = puzzles[0].model_copy(update={"source": puzzles[0].source.model_copy(update={"reveals": reveals})})
    sheets = materials_sheets(game.model_copy(update={"puzzles": puzzles}))
    paragraphs = [
        item for sheet in sheets if isinstance(sheet.content, ResultsPage) for item in sheet.content.paragraphs
    ]
    parts = [item for item in paragraphs if item.reveals and item.reveals in reveals]
    assert len(parts) > 1
    assert len({part.number for part in parts}) == 1
    assert [part.continued for part in parts] == [False] + [True] * (len(parts) - 1)
    assert parts[0].message.startswith("Correct!") and parts[1].message == ""
    assert parts[-1].action == "Open Envelope B now." and parts[0].action == ""
