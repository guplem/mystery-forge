"""The nonogram mechanic: row and column clues whose one solution is a picture of the answer.

The picture is the answer drawn in a 3x5 pixel font, or a bitmap that the agent gives. The builder proves that the
clues allow exactly one picture: a line solver fills every cell that line logic forces, and a bounded backtracking
search counts the solutions (up to 2) when line logic stalls.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)

type Clue = list[int]
type Line = list[int]
type Grid = list[Line]

UNKNOWN: int = -1
EMPTY: int = 0
FILLED: int = 1
MAXIMUM_WIDTH: int = 25
MAXIMUM_HEIGHT: int = 10
GLYPH_WIDTH: int = 3
NONOGRAM_NODE_BUDGET: int = 2000

# Blocky glyphs on purpose: a lone diagonal pair of pixels lets two pictures share the same clues. With these glyphs,
# every glyph and every pair of glyphs has clues with one solution.
PIXEL_FONT: dict[str, tuple[str, ...]] = {
    "A": ("###", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": ("###", "#..", "#..", "#..", "###"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
    "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "J": ("..#", "..#", "..#", "#.#", "###"),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"),
    "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#.#", "###", "###", "#.#", "#.#"),
    "N": ("##.", "#.#", "#.#", "#.#", "#.#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."),
    "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", "##.", ".##"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": ("###", "#..", "###", "..#", "###"),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"),
    "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#.#", "#.#", "###", "###", "#.#"),
    "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "Z": ("###", "..#", ".#.", "#..", "###"),
    "0": ("###", "#.#", "#.#", "#.#", "###"),
    "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("###", "..#", "###", "#..", "###"),
    "3": ("###", "..#", "###", "..#", "###"),
    "4": ("#.#", "#.#", "###", "..#", "..#"),
    "5": ("###", "#..", "##.", "..#", "##."),
    "6": (".##", "#..", "###", "#.#", "###"),
    "7": ("###", "..#", ".#.", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"),
    "9": ("###", "#.#", "###", "..#", "##."),
}
CHARACTER_BY_GLYPH: dict[tuple[str, ...], str] = {glyph: character for character, glyph in PIXEL_FONT.items()}
BITMAP_FIX_HINT: str = "Draw the bitmap as rows of '#' and '.' of the same width, at most 25 by 10."


class NonogramParams(BaseModel):
    bitmap: list[str] | None = Field(
        default=None,
        description="The picture as rows of '#' (filled) and '.' (empty), at most 25 by 10. Leave it out to draw "
        "the answer in the pixel font (at most 6 letters or digits).",
    )

    @field_validator("bitmap", mode="before")
    @classmethod
    def split_bitmap(cls, value: object) -> object:
        """Let a YAML text value such as "#.# / .#." stand for the rows."""
        if isinstance(value, str):
            return [row for row in re.split(r"[\s/]+", value) if row]
        return value


class SearchLimitReached(Exception):
    """The backtracking search used its whole node budget."""


def reachable_prefixes(line: Line, clue: Clue) -> list[list[bool]]:
    """`result[i][j]`: the first i cells can hold exactly the first j blocks, and cell i - 1 can be empty."""
    result: list[list[bool]] = [[False] * (len(clue) + 1) for _cell in range(len(line) + 1)]
    result[0][0] = True
    for end in range(1, len(line) + 1):
        if line[end - 1] == FILLED:
            continue
        for block_count in range(len(clue) + 1):
            if result[end - 1][block_count]:
                result[end][block_count] = True
                continue
            if block_count == 0:
                continue
            start: int = end - 1 - clue[block_count - 1]
            if start >= 0 and result[start][block_count - 1] and EMPTY not in line[start : end - 1]:
                result[end][block_count] = True
    return result


def solve_line(line: Line, clue: Clue) -> Line | None:
    """Return the line with every cell that all fitting arrangements agree on, or None when no arrangement fits."""
    padded: Line = [EMPTY, *line, EMPTY]
    size: int = len(padded)
    block_count: int = len(clue)
    forward: list[list[bool]] = reachable_prefixes(padded, clue)
    backward: list[list[bool]] = reachable_prefixes(padded[::-1], clue[::-1])
    if not forward[size][block_count]:
        return None
    can_be_empty: list[bool] = [
        padded[cell] != FILLED
        and any(
            forward[cell + 1][done] and backward[size - cell][block_count - done] for done in range(block_count + 1)
        )
        for cell in range(size)
    ]
    can_be_filled: list[bool] = [False] * size
    for index, length in enumerate(clue):
        for start in range(1, size - length):
            end: int = start + length
            if (
                forward[start][index]
                and EMPTY not in padded[start:end]
                and backward[size - end][block_count - index - 1]
            ):
                can_be_filled[start:end] = [True] * length
    solved: Line = []
    for cell in range(1, size - 1):
        if can_be_filled[cell] and can_be_empty[cell]:
            solved.append(UNKNOWN)
        elif can_be_filled[cell]:
            solved.append(FILLED)
        else:
            solved.append(EMPTY)
    return solved


def propagate(grid: Grid, row_clues: list[Clue], column_clues: list[Clue]) -> bool:
    """Apply line logic until nothing changes. Return False when a line has no fitting arrangement."""
    changed: bool = True
    while changed:
        changed = False
        for row_index, clue in enumerate(row_clues):
            solved: Line | None = solve_line(grid[row_index], clue)
            if solved is None:
                return False
            if solved != grid[row_index]:
                grid[row_index] = solved
                changed = True
        for column_index, clue in enumerate(column_clues):
            solved = solve_line([row[column_index] for row in grid], clue)
            if solved is None:
                return False
            for row_index, value in enumerate(solved):
                if grid[row_index][column_index] != value:
                    grid[row_index][column_index] = value
                    changed = True
    return True


class SolutionCounter:
    def __init__(self, row_clues: list[Clue], column_clues: list[Clue]) -> None:
        self.row_clues: list[Clue] = row_clues
        self.column_clues: list[Clue] = column_clues
        self.nodes_left: int = NONOGRAM_NODE_BUDGET
        self.solutions: list[Grid] = []

    def explore(self, grid: Grid) -> None:
        if len(self.solutions) >= 2 or not propagate(grid, self.row_clues, self.column_clues):
            return
        unknown_cells: list[tuple[int, int]] = [
            (row, column) for row, line in enumerate(grid) for column, value in enumerate(line) if value == UNKNOWN
        ]
        if not unknown_cells:
            self.solutions.append(grid)
            return
        if self.nodes_left <= 0:
            raise SearchLimitReached
        self.nodes_left -= 1
        row, column = unknown_cells[0]
        for value in (FILLED, EMPTY):
            guess: Grid = [list(line) for line in grid]
            guess[row][column] = value
            self.explore(guess)


def count_solutions(row_clues: list[Clue], column_clues: list[Clue]) -> tuple[int, Grid | None]:
    """Return the number of solutions (0, 1, or 2 for "2 or more") and the first one. Raise `SearchLimitReached`."""
    counter: SolutionCounter = SolutionCounter(row_clues, column_clues)
    counter.explore([[UNKNOWN] * len(column_clues) for _row in row_clues])
    return len(counter.solutions), (counter.solutions[0] if counter.solutions else None)


def line_clue(line: Line) -> Clue:
    return [len(run) for run in "".join("#" if value == FILLED else "." for value in line).split(".") if run]


def answer_picture(context: MechanicContext) -> Grid:
    answer: str = context.normalized_answer.upper()
    if not answer:
        raise MechanicBuildError(
            "The answer has no letters or digits.",
            fix_hint="Give the puzzle an answer with at least one letter or digit.",
        )
    most_characters: int = (MAXIMUM_WIDTH + 1) // (GLYPH_WIDTH + 1)
    if len(answer) > most_characters:
        raise MechanicBuildError(
            f"The answer has {len(answer)} letters, but the pixel font fits at most {most_characters} in "
            f"{MAXIMUM_WIDTH} columns.",
            fix_hint="Use a shorter answer, or draw the picture with the bitmap parameter.",
        )
    rows: list[str] = [".".join(PIXEL_FONT[character][row] for character in answer) for row in range(5)]
    return [[FILLED if pixel == "#" else EMPTY for pixel in row] for row in rows]


def bitmap_picture(bitmap: list[str]) -> Grid:
    def bitmap_error(message: str) -> MechanicBuildError:
        return MechanicBuildError(message, fix_hint=BITMAP_FIX_HINT)

    if len({len(row) for row in bitmap}) != 1:
        raise bitmap_error("The bitmap rows have different widths.")
    for character in "".join(bitmap):
        if character not in "#.":
            raise bitmap_error(f"The bitmap holds the character '{character}'. Use only '#' (filled) and '.' (empty).")
    if len(bitmap[0]) > MAXIMUM_WIDTH or len(bitmap) > MAXIMUM_HEIGHT:
        raise bitmap_error(
            f"The bitmap is {len(bitmap[0])} columns by {len(bitmap)} rows; the limit is {MAXIMUM_WIDTH} columns by "
            f"{MAXIMUM_HEIGHT} rows."
        )
    if "#" not in "".join(bitmap):
        raise bitmap_error("The bitmap has no filled cell.")
    return [[FILLED if pixel == "#" else EMPTY for pixel in row] for row in bitmap]


def require_one_solution(row_clues: list[Clue], column_clues: list[Clue]) -> None:
    try:
        count, _solution = count_solutions(row_clues, column_clues)
    except SearchLimitReached as error:
        raise MechanicBuildError(
            "The builder could not prove within its limit that the clues allow one solution.",
            fix_hint="Use a simpler picture or a shorter answer.",
        ) from error
    if count != 1:
        raise MechanicBuildError(
            "The clues of this picture allow more than one solution.",
            fix_hint="Change the picture or the answer, so that the clues allow only one solution.",
        )


def clue_text(clue: Clue) -> str:
    return " ".join(str(length) for length in clue) or "0"


def nonogram_table_html(row_clues: list[Clue], column_clues: list[Clue]) -> str:
    """Separate the cells with tabs, so the tag-free text keeps the same cell borders as the browser text."""
    header: str = "\t".join(
        ["<th></th>", *(f'<th class="mf-nonogram-column-clue">{clue_text(clue)}</th>' for clue in column_clues)]
    )
    rows: list[str] = [
        "<tr>"
        + "\t".join([f'<th class="mf-nonogram-row-clue">{clue_text(clue)}</th>', *(["<td></td>"] * len(column_clues))])
        + "</tr>"
        for clue in row_clues
    ]
    return "\n".join(['<table class="mf-nonogram">', f"<tr>{header}</tr>", *rows, "</table>"])


def build_nonogram(params: NonogramParams, context: MechanicContext) -> Artifact:
    picture: Grid = answer_picture(context) if params.bitmap is None else bitmap_picture(params.bitmap)
    row_clues: list[Clue] = [line_clue(row) for row in picture]
    column_clues: list[Clue] = [line_clue([row[column] for row in picture]) for column in range(len(picture[0]))]
    require_one_solution(row_clues, column_clues)
    return Artifact(
        html=nonogram_table_html(row_clues, column_clues),
        solver_text="\n".join(
            [
                "Rows (top to bottom):",
                *(clue_text(clue) for clue in row_clues),
                "Columns (left to right):",
                *(clue_text(clue) for clue in column_clues),
            ]
        ),
    )


def parse_clue(text: str) -> Clue:
    return [int(number) for number in text.split() if number != "0"]


def clues_from_text(text: str) -> tuple[list[Clue], list[Clue]]:
    """Read the clues back: the first line holds the column clues, each next line starts with a row clue."""
    lines: list[str] = [line for line in text.splitlines() if line.strip()]
    column_clues: list[Clue] = [parse_clue(field) for field in lines[0].split("\t") if field.strip()]
    row_clues: list[Clue] = [
        parse_clue(next(field for field in line.split("\t") if field.strip())) for line in lines[1:]
    ]
    return row_clues, column_clues


def read_glyphs(solution: Grid) -> str:
    characters: list[str] = []
    for index in range((len(solution[0]) + 1) // (GLYPH_WIDTH + 1)):
        first_column: int = index * (GLYPH_WIDTH + 1)
        glyph: tuple[str, ...] = tuple(
            "".join("#" if value == FILLED else "." for value in row[first_column : first_column + GLYPH_WIDTH])
            for row in solution
        )
        characters.append(CHARACTER_BY_GLYPH.get(glyph, "?"))
    return "".join(characters)


def decode_nonogram(rendered: RenderedArtifact, params: NonogramParams, context: MechanicContext) -> str:
    """Solve the clues read from the page text. Read the picture with the pixel font, or compare it with the bitmap.

    A bitmap picture has no letters to read, so the decoder returns the answer only when the solution is the bitmap.
    """
    row_clues, column_clues = clues_from_text(rendered.text)
    try:
        count, solution = count_solutions(row_clues, column_clues)
    except SearchLimitReached:
        return ""
    if count != 1 or solution is None:
        return ""
    if params.bitmap is not None:
        return context.answer if solution == bitmap_picture(params.bitmap) else ""
    return read_glyphs(solution)


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(
        id="nonogram", params_model=NonogramParams, build=build_nonogram, decode_rendered=decode_nonogram
    ),
)
