import html
import re
import time
from typing import Any

import pytest

from mystery_forge.mechanics import grids, registry
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)

SEA_WORDS: list[str] = [
    "anchor",
    "beacon",
    "harbor",
    "island",
    "ocean",
    "pirate",
    "sailor",
    "ship",
    "storm",
    "tide",
    "wave",
]
ALL_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1))
ALLOWED: dict[str, tuple[tuple[int, int], ...]] = {
    "easy": ALL_DIRECTIONS[:2],
    "medium": ALL_DIRECTIONS[:4],
    "hard": ALL_DIRECTIONS,
}


def make_context(answer: str, seed: int = 11, language: str = "en") -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language=language, seed=seed, documents={})


def implementation(mechanic_id: str) -> MechanicImplementation[Any]:
    return registry.all_implementations()[mechanic_id]


def build(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    chosen: MechanicImplementation[Any] = implementation(mechanic_id)
    return chosen.build(parse_params(chosen, raw_params), context)


def stripped_text(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def tabbed_text(markup: str) -> str:
    """Imitate the browser innerText of a table: a tab after each cell, no source whitespace between cells."""
    compact: str = re.sub(r">\s+<", "><", markup)
    return stripped_text(re.sub(r"</t[dh]>", "\t", re.sub(r"</tr>", "\n", compact)))


def decode(
    mechanic_id: str, raw_params: dict[str, Any], text: str, artifact: Artifact, context: MechanicContext
) -> str:
    chosen: MechanicImplementation[Any] = implementation(mechanic_id)
    assert chosen.decode_rendered is not None
    return chosen.decode_rendered(
        RenderedArtifact(text=text, html=artifact.html), parse_params(chosen, raw_params), context
    )


def expect_build_error(mechanic_id: str, raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(mechanic_id, raw_params, context)
    return raised.value


def table_rows(markup: str, table_class: str) -> list[list[str]]:
    table: str = re.findall(rf'<table class="[^"]*{table_class}[^"]*"[^>]*>(.*?)</table>', markup, flags=re.DOTALL)[0]
    rows: list[list[str]] = [
        re.findall(r"<td[^>]*>(.*?)</td>", row) for row in re.findall(r"<tr>(.*?)</tr>", table, flags=re.DOTALL)
    ]
    return [row for row in rows if row]


def occurrences(
    grid: list[list[str]], word: str, directions: tuple[tuple[int, int], ...]
) -> set[frozenset[tuple[int, int]]]:
    found: set[frozenset[tuple[int, int]]] = set()
    size: int = len(grid)
    for row in range(size):
        for column in range(size):
            for row_step, column_step in directions:
                cells: list[tuple[int, int]] = [
                    (row + index * row_step, column + index * column_step) for index in range(len(word))
                ]
                if all(0 <= r < size and 0 <= c < size for r, c in cells) and all(
                    grid[r][c] == letter for (r, c), letter in zip(cells, word, strict=True)
                ):
                    found.add(frozenset(cells))
    return found


@pytest.mark.parametrize("mechanic_id", ["word-search", "grid-coordinates", "overlay-mask"])
def test_grid_mechanics_are_registered(mechanic_id: str) -> None:
    assert implementation(mechanic_id) in grids.IMPLEMENTATIONS


# word-search


@pytest.mark.parametrize("directions", ["easy", "medium", "hard"])
def test_word_search_places_each_word_once_and_the_leftover_cells_spell_the_answer(directions: str) -> None:
    started: float = time.perf_counter()
    artifact: Artifact = build(
        "word-search", {"words": SEA_WORDS, "directions": directions}, make_context("Lighthouse")
    )
    assert time.perf_counter() - started < 2
    grid: list[list[str]] = table_rows(artifact.html, "mf-word-search")
    assert len({len(row) for row in grid}) == 1
    assert len(grid) == len(grid[0])
    covered: set[tuple[int, int]] = set()
    for word in SEA_WORDS:
        found: set[frozenset[tuple[int, int]]] = occurrences(grid, word.upper(), ALLOWED[directions])
        assert len(found) == 1, word
        covered |= next(iter(found))
    leftover: str = "".join(
        grid[row][column] for row in range(len(grid)) for column in range(len(grid)) if (row, column) not in covered
    )
    assert leftover == "LIGHTHOUSE"
    assert "ANCHOR" in artifact.solver_text
    assert '<ul class="mf-word-list">' in artifact.html


def test_word_search_uses_the_given_size() -> None:
    words: list[str] = [*SEA_WORDS, "compass", "mermaid", "shells"]
    artifact: Artifact = build("word-search", {"words": words, "size": "9"}, make_context("keeper"))
    assert len(table_rows(artifact.html, "mf-word-search")) == 9


def test_word_search_accepts_a_comma_separated_word_list_and_folds_accents() -> None:
    word_text: str = ", ".join(SEA_WORDS).replace("sailor", "mástil")
    params = parse_params(implementation("word-search"), {"words": word_text})
    assert isinstance(params, grids.WordSearchParams)
    assert params.words[6] == "mástil"
    artifact: Artifact = build("word-search", {"words": params.words}, make_context("Señales", language="es"))
    assert "<li>MASTIL</li>" in artifact.html


def test_word_search_is_deterministic() -> None:
    params: dict[str, Any] = {"words": SEA_WORDS}
    assert build("word-search", params, make_context("lighthouse", seed=4)) == build(
        "word-search", params, make_context("lighthouse", seed=4)
    )


@pytest.mark.parametrize("directions", ["easy", "medium", "hard"])
def test_word_search_round_trip(directions: str) -> None:
    params: dict[str, Any] = {"words": SEA_WORDS, "directions": directions}
    context: MechanicContext = make_context("lighthouse")
    artifact: Artifact = build("word-search", params, context)
    assert decode("word-search", params, stripped_text(artifact.html), artifact, context) == "LIGHTHOUSE"
    assert decode("word-search", params, tabbed_text(artifact.html), artifact, context) == "LIGHTHOUSE"


def test_word_search_rejects_a_word_with_a_bad_length() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": ["ox", *SEA_WORDS[:4]]}, make_context("lighthouse")
    )
    assert error.message == "The word 'ox' has 2 letters; each word needs 3 to 12 letters."
    assert error.fix_hint == "Replace the word 'ox' with a word of 3 to 12 letters."


def test_word_search_rejects_a_word_with_digits() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": ["room101", *SEA_WORDS[:4]]}, make_context("lighthouse")
    )
    assert error.message == "The word 'room101' has characters that are not letters."
    assert error.fix_hint == "Use words that hold only letters."


def test_word_search_rejects_duplicate_words() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": ["Faro", "faró", *SEA_WORDS[:4]]}, make_context("lighthouse")
    )
    assert error.message == "The word 'FARO' appears twice in the word list."
    assert error.fix_hint == "Remove the repeated word."


def test_word_search_rejects_a_word_inside_another_word() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": ["ship", "shipwreck", *SEA_WORDS[:4]]}, make_context("lighthouse")
    )
    assert error.message == "The word 'SHIP' is inside the word 'SHIPWRECK', so it appears twice."
    assert error.fix_hint == "Remove one of the two words."


def test_word_search_rejects_a_reversed_word_inside_another_word_only_in_hard_mode() -> None:
    words: list[str] = ["tops", "spotless", *SEA_WORDS[:4]]
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": words, "directions": "hard"}, make_context("lighthouse")
    )
    assert error.message == "The word 'TOPS' is inside the word 'SPOTLESS', so it appears twice."
    with pytest.raises(MechanicBuildError) as raised:
        build("word-search", {"words": words, "directions": "medium"}, make_context("lighthouse"))
    assert "inside" not in raised.value.message


def test_word_search_rejects_a_word_longer_than_the_grid() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": ["lighthousekeeper"[:12], *SEA_WORDS[:4]], "size": 8}, make_context("x")
    )
    assert error.message == "The word 'LIGHTHOUSEKE' has 12 letters, more than the grid size 8."
    assert error.fix_hint == "Use a bigger size or a shorter word."


def test_word_search_rejects_words_with_too_few_letters_to_fill_the_grid() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": SEA_WORDS[:4], "size": 8}, make_context("lighthouse")
    )
    assert error.message == (
        "In a 8x8 grid, the words must cover 54 cells, so that the 10 cells left over spell the answer. "
        "The words have only 24 letters."
    )
    assert error.fix_hint == "Add words, use longer words, or use a smaller size."


def test_word_search_rejects_words_with_too_many_letters_for_the_grid() -> None:
    error: MechanicBuildError = expect_build_error(
        "word-search", {"words": SEA_WORDS, "size": 8}, make_context("a" * 60)
    )
    assert error.message == "In a 8x8 grid, 60 answer letters leave only 4 cells for words with 58 letters."
    assert error.fix_hint == "Remove words, use shorter words, use a bigger size, or use a shorter answer."


def test_word_search_without_a_size_reports_that_no_size_fits() -> None:
    error: MechanicBuildError = expect_build_error("word-search", {"words": SEA_WORDS[:4]}, make_context("lighthouse"))
    assert error.message == "No grid size from 8 to 15 fits 24 word letters and 10 answer letters."
    assert error.fix_hint == "Add words, use longer words, or use a shorter answer."


def test_word_search_reports_a_failed_search(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grids, "WORD_SEARCH_NODE_BUDGET", 1)
    error: MechanicBuildError = expect_build_error("word-search", {"words": SEA_WORDS}, make_context("lighthouse"))
    assert error.message == "The builder found no layout where the words leave exactly the answer letters."
    assert error.fix_hint == (
        "Change the words so that they have 54 to 62 letters in total (the 8x8 grid needs 54 covered cells), "
        "or change the size."
    )


def test_word_search_rejects_an_answer_without_letters() -> None:
    error: MechanicBuildError = expect_build_error("word-search", {"words": SEA_WORDS}, make_context("!!"))
    assert error.message == "The answer has no letters or digits."


def test_word_search_rejects_a_bad_word_count() -> None:
    with pytest.raises(MechanicBuildError):
        parse_params(implementation("word-search"), {"words": "ship, tide, wave"})


# grid-coordinates


def coordinate_grid(artifact: Artifact) -> tuple[list[str], list[list[str]]]:
    header: list[str] = re.findall(r"<th>(.*?)</th>", re.findall(r"<tr>(.*?)</tr>", artifact.html)[0])
    return header, table_rows(artifact.html, "mf-grid-coordinates")


def test_grid_coordinates_letters_at_the_coordinates_spell_the_answer() -> None:
    artifact: Artifact = build("grid-coordinates", {"size": "6"}, make_context("Faro", seed=2))
    header, grid = coordinate_grid(artifact)
    assert header == ["", "A", "B", "C", "D", "E", "F"]
    assert len(grid) == 6
    coordinates: list[str] = re.findall(r'data-coordinates="([^"]*)"', artifact.html)[0].split()
    assert len(set(coordinates)) == 4
    letters: str = "".join(grid[int(code[1:]) - 1][ord(code[0]) - ord("A")] for code in coordinates)
    assert letters == "FARO"
    # The sheet does not print the list, so the packet must not show it: a document of the writer prints it.
    assert "Coordinates" not in artifact.solver_text
    assert artifact.needs_in_documents == tuple(coordinates)
    assert re.search(r"<th>6</th>", artifact.html)


def test_grid_coordinates_uses_the_given_coordinates() -> None:
    params: dict[str, Any] = {"size": 5, "coordinates": "a1, E5 c3 a1"}
    artifact: Artifact = build("grid-coordinates", params, make_context("TOPT"))
    _header, grid = coordinate_grid(artifact)
    assert (grid[0][0], grid[4][4], grid[2][2]) == ("T", "O", "P")


def test_grid_coordinates_is_deterministic() -> None:
    assert build("grid-coordinates", {}, make_context("faro", seed=8)) == build(
        "grid-coordinates", {}, make_context("faro", seed=8)
    )


def test_grid_coordinates_round_trip() -> None:
    context: MechanicContext = make_context("Room 101")
    artifact: Artifact = build("grid-coordinates", {}, context)
    assert decode("grid-coordinates", {}, stripped_text(artifact.html), artifact, context) == "ROOM101"
    assert decode("grid-coordinates", {}, tabbed_text(artifact.html), artifact, context) == "ROOM101"


def test_grid_coordinates_rejects_a_coordinate_count_that_differs_from_the_answer() -> None:
    error: MechanicBuildError = expect_build_error("grid-coordinates", {"coordinates": "A1 B2"}, make_context("faro"))
    assert error.message == "There are 2 coordinates, but the answer 'FARO' has 4 letters."
    assert error.fix_hint == "Give one coordinate per answer letter, or leave out the coordinates."


@pytest.mark.parametrize("code", ["11", "AA1", "A0", "I1", "A9"])
def test_grid_coordinates_rejects_a_coordinate_outside_the_grid(code: str) -> None:
    error: MechanicBuildError = expect_build_error(
        "grid-coordinates", {"size": 8, "coordinates": [code]}, make_context("f")
    )
    assert error.message == f"The coordinate '{code}' is not a cell of the 8x8 grid."
    assert error.fix_hint == "Write each coordinate as a column letter A to H and a row number 1 to 8, such as C4."


def test_grid_coordinates_rejects_one_cell_with_two_letters() -> None:
    error: MechanicBuildError = expect_build_error("grid-coordinates", {"coordinates": "A1 A1"}, make_context("ab"))
    assert error.message == "The coordinate 'A1' must hold both 'A' and 'B'."
    assert error.fix_hint == "Use a different coordinate for each different letter."


def test_grid_coordinates_rejects_an_answer_longer_than_the_grid() -> None:
    error: MechanicBuildError = expect_build_error("grid-coordinates", {"size": 5}, make_context("a" * 26))
    assert error.message == "The answer has 26 letters, more than the 25 cells of the grid."
    assert error.fix_hint == "Use a bigger size."


def test_grid_coordinates_rejects_an_answer_without_letters() -> None:
    assert (
        expect_build_error("grid-coordinates", {}, make_context("-")).message == "The answer has no letters or digits."
    )


# overlay-mask


def test_overlay_mask_holes_show_the_answer_in_reading_order() -> None:
    artifact: Artifact = build("overlay-mask", {"size": "5"}, make_context("Faro", seed=6))
    grid: list[list[str]] = table_rows(artifact.html, "mf-overlay-grid")
    mask: list[list[str]] = [
        re.findall(r"<td( class=\"mf-mask-hole\")?></td>", row)
        for row in re.findall(r"<tr>(.*?)</tr>", artifact.html.split('class="mf-mask"')[1], flags=re.DOTALL)
    ]
    assert len(grid) == 5
    assert len(mask) == 5
    letters: str = "".join(
        grid[row][column] for row in range(5) for column in range(5) if mask[row][column] == ' class="mf-mask-hole"'
    )
    assert letters == "FARO"
    assert artifact.print_notes == ("Cut out the pale squares (the windows) of the dark mask card.",)
    assert "(# = a window in the mask card)" in artifact.solver_text


def test_overlay_mask_is_deterministic() -> None:
    assert build("overlay-mask", {}, make_context("faro", seed=1)) == build(
        "overlay-mask", {}, make_context("faro", seed=1)
    )


def test_overlay_mask_round_trip() -> None:
    context: MechanicContext = make_context("Ancla 7")
    artifact: Artifact = build("overlay-mask", {}, context)
    assert decode("overlay-mask", {}, stripped_text(artifact.html), artifact, context) == "ANCLA7"
    assert decode("overlay-mask", {}, tabbed_text(artifact.html), artifact, context) == "ANCLA7"


def test_overlay_mask_rejects_an_answer_longer_than_the_grid() -> None:
    error: MechanicBuildError = expect_build_error("overlay-mask", {"size": 4}, make_context("a" * 17))
    assert error.message == "The answer has 17 letters, more than the 16 cells of the grid."
    assert error.fix_hint == "Use a bigger size."


def test_overlay_mask_rejects_an_answer_without_letters() -> None:
    assert expect_build_error("overlay-mask", {}, make_context("?")).message == "The answer has no letters or digits."
