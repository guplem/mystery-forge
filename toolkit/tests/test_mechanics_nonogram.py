import html
import itertools
import random
import re
import time
from typing import Any

import pytest

from mystery_forge.mechanics import nonogram, registry
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)


def make_context(answer: str, seed: int = 1) -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language="en", seed=seed, documents={})


def implementation() -> MechanicImplementation[Any]:
    return registry.all_implementations()["nonogram"]


def build(raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    return implementation().build(parse_params(implementation(), raw_params), context)


def decode(raw_params: dict[str, Any], text: str, artifact: Artifact, context: MechanicContext) -> str:
    decoder = implementation().decode_rendered
    assert decoder is not None
    return decoder(RenderedArtifact(text=text, html=artifact.html), parse_params(implementation(), raw_params), context)


def stripped_text(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def line_clue(cells: list[bool]) -> list[int]:
    return [len(run) for run in "".join("#" if cell else "." for cell in cells).split(".") if run]


def picture_clues(picture: list[str]) -> tuple[list[list[int]], list[list[int]]]:
    rows: list[list[int]] = [line_clue([cell == "#" for cell in row]) for row in picture]
    columns: list[list[int]] = [line_clue([row[column] == "#" for row in picture]) for column in range(len(picture[0]))]
    return rows, columns


def rendered_clues(artifact: Artifact) -> tuple[list[str], list[str]]:
    columns: list[str] = re.findall(r'<th class="mf-nonogram-column-clue">([^<]*)</th>', artifact.html)
    rows: list[str] = re.findall(r'<th class="mf-nonogram-row-clue">([^<]*)</th>', artifact.html)
    return rows, columns


def clue_text(clue: list[int]) -> str:
    return " ".join(str(length) for length in clue) or "0"


def font_picture(text: str) -> list[str]:
    return [".".join(nonogram.PIXEL_FONT[character][row] for character in text) for row in range(5)]


def brute_force_solution_count(row_clues: list[list[int]], column_clues: list[list[int]]) -> int:
    height: int = len(row_clues)
    width: int = len(column_clues)
    count: int = 0
    for bits in itertools.product([False, True], repeat=height * width):
        rows: list[list[bool]] = [list(bits[row * width : (row + 1) * width]) for row in range(height)]
        if [line_clue(row) for row in rows] == row_clues and [
            line_clue([rows[row][column] for row in range(height)]) for column in range(width)
        ] == column_clues:
            count += 1
    return count


def test_nonogram_is_registered() -> None:
    assert implementation() in nonogram.IMPLEMENTATIONS


def test_pixel_font_has_distinct_three_by_five_glyphs_for_every_letter_and_digit() -> None:
    assert sorted(nonogram.PIXEL_FONT) == sorted("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    for glyph in nonogram.PIXEL_FONT.values():
        assert len(glyph) == 5
        assert all(len(row) == 3 and set(row) <= {"#", "."} for row in glyph)
    assert len(set(nonogram.PIXEL_FONT.values())) == 36


@pytest.mark.parametrize(
    "answer",
    [*nonogram.PIXEL_FONT, "LLAVE", "CLOCK", "POISON", "SAFE", "VAULT", "1923", "SHIP", "ROSA", "CASA", "CAJA"],
)
def test_nonogram_pixel_font_words_have_one_solution(answer: str) -> None:
    rows, columns = picture_clues(font_picture(answer))
    assert nonogram.count_solutions(rows, columns)[0] == 1


def test_nonogram_clues_describe_the_answer_in_the_pixel_font() -> None:
    started: float = time.perf_counter()
    artifact: Artifact = build({}, make_context("Faro"))
    assert time.perf_counter() - started < 2
    expected_rows, expected_columns = picture_clues(font_picture("FARO"))
    rows, columns = rendered_clues(artifact)
    assert rows == [clue_text(clue) for clue in expected_rows]
    assert columns == [clue_text(clue) for clue in expected_columns]
    assert len(re.findall(r"<td></td>", artifact.html)) == 5 * 15
    assert artifact.solver_text.startswith("Rows (top to bottom):")
    assert "Columns (left to right):" in artifact.solver_text


def test_nonogram_counts_solutions_like_a_brute_force_search_on_small_grids() -> None:
    rng: random.Random = random.Random(4)
    for _case in range(40):
        picture: list[str] = ["".join(rng.choice("#.") for _column in range(4)) for _row in range(3)]
        row_clues, column_clues = picture_clues(picture)
        expected: int = min(2, brute_force_solution_count(row_clues, column_clues))
        count, _solution = nonogram.count_solutions(row_clues, column_clues)
        assert count == expected, picture


def test_nonogram_line_solver_finds_the_cells_that_every_arrangement_shares() -> None:
    unknown: int = nonogram.UNKNOWN
    assert nonogram.solve_line([unknown] * 5, [4]) == [unknown, 1, 1, 1, unknown]
    assert nonogram.solve_line([unknown] * 5, [1, 3]) == [1, 0, 1, 1, 1]
    assert nonogram.solve_line([unknown] * 3, []) == [0, 0, 0]
    assert nonogram.solve_line([1, unknown, unknown], [1]) == [1, 0, 0]
    assert nonogram.solve_line([1, 1, unknown], [1]) is None


def test_nonogram_is_deterministic() -> None:
    assert build({}, make_context("key")) == build({}, make_context("key", seed=99))


@pytest.mark.parametrize("answer", ["Faro", "KEY", "Room 7"])
def test_nonogram_round_trip(answer: str) -> None:
    context: MechanicContext = make_context(answer)
    artifact: Artifact = build({}, context)
    assert decode({}, stripped_text(artifact.html), artifact, context) == context.normalized_answer.upper()


def test_nonogram_round_trip_with_browser_style_text() -> None:
    context: MechanicContext = make_context("key")
    artifact: Artifact = build({}, context)
    compact: str = re.sub(r">\s+<", "><", artifact.html)
    text: str = stripped_text(re.sub(r"</t[dh]>", "\t", re.sub(r"</tr>", "\n", compact)))
    assert decode({}, text, artifact, context) == "KEY"


HOUSE: list[str] = ["..#..", ".###.", "#####", "#.#.#", "###.#"]


def test_nonogram_builds_a_given_bitmap_and_decodes_it() -> None:
    params: dict[str, Any] = {"bitmap": " / ".join(HOUSE)}
    context: MechanicContext = make_context("house")
    artifact: Artifact = build(params, context)
    rows, columns = rendered_clues(artifact)
    expected_rows, expected_columns = picture_clues(HOUSE)
    assert rows == [clue_text(clue) for clue in expected_rows]
    assert columns == [clue_text(clue) for clue in expected_columns]
    assert decode(params, stripped_text(artifact.html), artifact, context) == "house"
    other: dict[str, Any] = {"bitmap": ["#####", "#####", "#####", "#####", "#####"]}
    assert decode(other, stripped_text(artifact.html), artifact, context) == ""


def test_nonogram_decode_returns_nothing_for_clues_without_one_solution() -> None:
    artifact: Artifact = build({"bitmap": "#. ##"}, make_context("x"))
    ambiguous_text: str = "\t1\t1\n1\t\t\n1\t\t\n"
    assert decode({}, ambiguous_text, artifact, make_context("x")) == ""


def test_nonogram_decode_shows_an_unknown_glyph_as_a_question_mark() -> None:
    context: MechanicContext = make_context("x")
    artifact: Artifact = build({"bitmap": HOUSE}, context)
    assert decode({}, stripped_text(artifact.html), artifact, context) == "?"


def test_nonogram_rejects_an_ambiguous_picture() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        build({"bitmap": "#. .#"}, make_context("x"))
    assert raised.value.message == "The clues of this picture allow more than one solution."
    assert raised.value.fix_hint == "Change the picture or the answer, so that the clues allow only one solution."


def test_nonogram_rejects_a_search_over_its_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nonogram, "NONOGRAM_NODE_BUDGET", 0)
    with pytest.raises(MechanicBuildError) as raised:
        build({"bitmap": "#. .#"}, make_context("x"))
    assert raised.value.message == "The builder could not prove within its limit that the clues allow one solution."
    assert raised.value.fix_hint == "Use a simpler picture or a shorter answer."


def test_nonogram_rejects_an_answer_too_long_for_the_font() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        build({}, make_context("lighthouse"))
    assert raised.value.message == "The answer has 10 letters, but the pixel font fits at most 6 in 25 columns."
    assert raised.value.fix_hint == "Use a shorter answer, or draw the picture with the bitmap parameter."


def test_nonogram_rejects_an_answer_without_letters() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        build({}, make_context("--"))
    assert raised.value.message == "The answer has no letters or digits."


@pytest.mark.parametrize(
    ("bitmap", "message"),
    [
        (["#.", "#"], "The bitmap rows have different widths."),
        (["#x"], "The bitmap holds the character 'x'. Use only '#' (filled) and '.' (empty)."),
        (["#" * 26], "The bitmap is 26 columns by 1 rows; the limit is 25 columns by 10 rows."),
        (["#"] * 11, "The bitmap is 1 columns by 11 rows; the limit is 25 columns by 10 rows."),
        (["..", ".."], "The bitmap has no filled cell."),
    ],
)
def test_nonogram_rejects_a_bad_bitmap(bitmap: list[str], message: str) -> None:
    with pytest.raises(MechanicBuildError) as raised:
        build({"bitmap": bitmap}, make_context("x"))
    assert raised.value.message == message
    assert raised.value.fix_hint == "Draw the bitmap as rows of '#' and '.' of the same width, at most 25 by 10."


def test_nonogram_html_is_safe() -> None:
    artifact: Artifact = build({}, make_context("key"))
    assert artifact.html.startswith('<table class="mf-nonogram">')
    assert "<script" not in artifact.html


def test_nonogram_counts_no_solution_for_clues_that_contradict_each_other() -> None:
    assert nonogram.count_solutions([[1]], [[]]) == (0, None)


def test_nonogram_decode_returns_nothing_when_the_search_reaches_its_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    context: MechanicContext = make_context("x")
    artifact: Artifact = build({"bitmap": HOUSE}, context)
    monkeypatch.setattr(nonogram, "NONOGRAM_NODE_BUDGET", 0)
    assert decode({}, "\t1\t1\n1\t\t\n1\t\t\n", artifact, context) == ""
