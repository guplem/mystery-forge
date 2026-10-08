import pytest

from mystery_forge.i18n import LANGUAGES
from mystery_forge.render.sheets import (
    OutputFileNames,
    OutputPlan,
    Sheet,
    number_sheets,
    number_sheets_by_stage,
    output_file_names,
    paginate,
)

# Windows refuses these characters in a file or folder name.
WINDOWS_FORBIDDEN: str = r'<>:"/\|?*'


def sheet(stage: str | None) -> Sheet:
    return Sheet(role="document", template="x.html.j2", content=None, stage=stage)


def test_paginate_fills_each_page_up_to_the_budget() -> None:
    assert paginate([3, 3, 3, 9, 1], lambda item: item, 6) == [[3, 3], [3], [9], [1]]
    assert paginate([], lambda item: item, 6) == []


def test_paginate_packs_a_tiny_last_page_into_slightly_fuller_pages() -> None:
    assert paginate([5, 5, 1], lambda item: item, 10) == [[5, 5, 1]]
    assert paginate([4, 4, 4, 4, 1], lambda item: item, 8.5) == [[4, 4], [4, 4, 1]]


def test_paginate_keeps_a_last_page_that_is_not_tiny_or_that_no_slight_stretch_absorbs() -> None:
    assert paginate([10, 10, 2], lambda item: item, 10) == [[10], [10], [2]]
    assert paginate([5, 5, 3], lambda item: item, 10) == [[5, 5], [3]]


def test_paginate_moves_a_heading_to_the_page_of_the_item_after_it() -> None:
    def is_heading(item: str) -> bool:
        return item.startswith("#")

    def cost(item: str) -> float:
        return 1 if is_heading(item) else 3

    assert paginate(["a", "#h", "b"], cost, 5, is_heading) == [["a"], ["#h", "b"]]
    assert paginate(["#h", "#i", "b"], cost, 4, is_heading) == [["#h", "#i", "b"]]


def test_number_sheets_counts_the_whole_output() -> None:
    assert [item.corner for item in number_sheets([sheet(None), sheet("A")])] == ["1/2", "2/2"]


def test_number_sheets_by_stage_counts_inside_each_stage() -> None:
    numbered = number_sheets_by_stage([sheet(None), sheet("A"), sheet("A"), sheet("B"), sheet(None)])
    assert [item.corner for item in numbered] == ["1/2", "A · 1/2", "A · 2/2", "B · 1/1", "2/2"]


def test_an_output_plan_keeps_a_language_neutral_html_file() -> None:
    assert OutputPlan(id="hints", sheets=[]).html_file == "hints.html"
    assert OutputPlan(id="materials", sheets=[]).html_file == "materials.html"


def test_the_output_file_names_follow_the_game_language() -> None:
    assert output_file_names("en") == OutputFileNames(
        pdfs={
            "manual": "1 - START HERE (manual).pdf",
            "materials": "2 - PRINT THIS (game materials).pdf",
            "hints": "3 - Hints.pdf",
            "solutions": "4 - Solutions.pdf",
        },
        companion="Game companion.html",
        warnings="0 - READ FIRST (warnings).txt",
        spoiler_folder="HOST ONLY - spoilers",
    )
    spanish = output_file_names("es")
    assert spanish.pdfs == {
        "manual": "1 - EMPIEZA AQUÍ (manual).pdf",
        "materials": "2 - IMPRIME ESTO (materiales del juego).pdf",
        "hints": "3 - Pistas.pdf",
        "solutions": "4 - Soluciones.pdf",
    }
    assert spanish.companion == "Compañero de juego.html"
    assert spanish.spoiler_folder == "SOLO ANFITRIÓN - spoilers"


def test_the_exported_path_puts_the_hints_and_the_solutions_in_the_spoiler_folder() -> None:
    names = output_file_names("es")
    assert names.exported_path("manual") == "1 - EMPIEZA AQUÍ (manual).pdf"
    assert names.exported_path("solutions") == "SOLO ANFITRIÓN - spoilers/4 - Soluciones.pdf"


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_names_the_files_in_reading_order_with_names_that_windows_accepts(language: str) -> None:
    names = output_file_names(language)
    pdfs = list(names.pdfs.values())
    assert [name[:4] for name in pdfs] == ["1 - ", "2 - ", "3 - ", "4 - "]
    assert all(name.endswith(".pdf") for name in pdfs)
    assert names.companion.endswith(".html")
    for name in (*pdfs, names.companion, names.spoiler_folder):
        assert not set(name) & set(WINDOWS_FORBIDDEN), name
        assert name == name.strip() and not name.endswith(".")
    if language != "en":
        assert pdfs != list(output_file_names("en").pdfs.values())
        assert names.spoiler_folder != output_file_names("en").spoiler_folder
