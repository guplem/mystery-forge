"""Letter-grid mechanics: word search, grid coordinates, and overlay mask.

Every grid renders as an HTML table with the class `mf-grid`, one letter per cell, so the letters stay in the page text.
The source HTML puts a space between cells and a line break between rows: the decoders then read the same grid from
the tag-free text and from the browser text (a tab after each cell).
"""

import random
import re
import string
from collections.abc import Iterator
from typing import Any, Literal

from markupsafe import escape
from pydantic import BaseModel, Field, field_validator

from mystery_forge.answers import normalize_answer
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)

type Cell = tuple[int, int]
type Step = tuple[int, int]
type LetterGrid = list[list[str]]

FILL_LETTERS: str = string.ascii_uppercase


def require_answer_letters(context: MechanicContext) -> str:
    """Return the answer as uppercase letters and digits, the form that the grids print."""
    if not context.normalized_answer:
        raise MechanicBuildError(
            "The answer has no letters or digits.",
            fix_hint="Give the puzzle an answer with at least one letter or digit.",
        )
    return context.normalized_answer.upper()


def all_cells(size: int) -> list[Cell]:
    return [(row, column) for row in range(size) for column in range(size)]


def filled_grid(size: int, letters_by_cell: dict[Cell, str], rng: random.Random) -> LetterGrid:
    """Return a grid with the given letters and a random letter in every other cell."""
    return [
        [letters_by_cell.get((row, column)) or rng.choice(FILL_LETTERS) for column in range(size)]
        for row in range(size)
    ]


def grid_table_html(grid: LetterGrid, css_class: str, attributes: str = "", labelled: bool = False) -> str:
    lines: list[str] = [f'<table class="mf-grid {css_class}"{attributes}>']
    if labelled:
        column_labels: str = " ".join(f"<th>{label}</th>" for label in FILL_LETTERS[: len(grid)])
        lines.append(f"<tr><th></th> {column_labels}</tr>")
    for row_number, row in enumerate(grid, start=1):
        label: str = f"<th>{row_number}</th> " if labelled else ""
        lines.append(f"<tr>{label}" + " ".join(f"<td>{escape(letter)}</td>" for letter in row) + "</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def grid_text(grid: LetterGrid) -> str:
    return "\n".join(" ".join(row) for row in grid)


def single_letter_rows(text: str, minimum_width: int) -> LetterGrid:
    """Return the text lines that hold only single-character tokens, at least `minimum_width` of them."""
    rows: LetterGrid = []
    for line in text.splitlines():
        tokens: list[str] = line.split()
        if len(tokens) >= minimum_width and all(len(token) == 1 for token in tokens):
            rows.append(tokens)
    return rows


def split_list_text(value: object, separators: str) -> object:
    """Let a YAML text value such as "ship, tide, wave" stand for a list."""
    if isinstance(value, str):
        return [part.strip() for part in re.split(separators, value) if part.strip()]
    return value


# word-search

# The layout search is heavy-tailed: many short searches with a fresh random order beat one long search.
WORD_SEARCH_NODE_BUDGET: int = 150
WORD_SEARCH_RESTARTS: int = 40
# Inputs whose words share up to about this share of the covered cells build reliably within the time limit.
COMFORTABLE_SHARED_LETTER_SHARE: float = 0.15
WORD_SEARCH_SIZES: range = range(8, 16)
MINIMUM_WORD_LENGTH: int = 3
MAXIMUM_WORD_LENGTH: int = 12
FORWARD_STEPS: tuple[Step, ...] = ((0, 1), (1, 0))
DIAGONAL_STEPS: tuple[Step, ...] = ((1, 1), (-1, 1))
REVERSED_STEPS: tuple[Step, ...] = ((0, -1), (-1, 0), (-1, -1), (1, -1))
STEPS_BY_DIRECTIONS: dict[str, tuple[Step, ...]] = {
    "easy": FORWARD_STEPS,
    "medium": FORWARD_STEPS + DIAGONAL_STEPS,
    "hard": FORWARD_STEPS + DIAGONAL_STEPS + REVERSED_STEPS,
}


class WordSearchParams(BaseModel):
    words: list[str] = Field(
        min_length=4, max_length=16, description="The words to find, 3 to 12 letters each. Accents do not count."
    )
    size: int | None = Field(
        default=None,
        ge=min(WORD_SEARCH_SIZES),
        le=max(WORD_SEARCH_SIZES),
        description="The number of rows and columns. Leave it out to let the builder pick a size that fits.",
    )
    directions: Literal["easy", "medium", "hard"] = Field(
        default="medium",
        description='"easy": right and down. "medium": also the two diagonals that read left to right. '
        '"hard": also every reversed direction.',
    )
    message_mode: Literal["leftover"] = Field(
        default="leftover",
        description='"leftover": the cells that no word uses, read row by row, spell the answer.',
    )

    @field_validator("words", mode="before")
    @classmethod
    def split_words(cls, value: object) -> object:
        return split_list_text(value, r"[,\n]")


def folded_words(words: list[str]) -> list[str]:
    folded_list: list[str] = []
    for word in words:
        folded: str = normalize_answer(word, "").upper()
        if not folded.isalpha():
            raise MechanicBuildError(
                f"The word '{word}' has characters that are not letters.", fix_hint="Use words that hold only letters."
            )
        if not MINIMUM_WORD_LENGTH <= len(folded) <= MAXIMUM_WORD_LENGTH:
            raise MechanicBuildError(
                f"The word '{word}' has {len(folded)} letters; each word needs 3 to 12 letters.",
                fix_hint=f"Replace the word '{word}' with a word of 3 to 12 letters.",
            )
        if folded in folded_list:
            raise MechanicBuildError(
                f"The word '{folded}' appears twice in the word list.", fix_hint="Remove the repeated word."
            )
        folded_list.append(folded)
    return folded_list


def reject_nested_words(words: list[str], reversed_allowed: bool) -> None:
    """A word inside another word would appear twice in the grid, so the player could not tell which one counts."""
    for inner in words:
        for outer in words:
            if inner != outer and (inner in outer or (reversed_allowed and inner[::-1] in outer)):
                raise MechanicBuildError(
                    f"The word '{inner}' is inside the word '{outer}', so it appears twice.",
                    fix_hint="Remove one of the two words.",
                )


def covered_cell_target(size: int, answer: str) -> int:
    return size * size - len(answer)


def size_fits(size: int, words: list[str], answer: str) -> bool:
    target: int = covered_cell_target(size, answer)
    return max(len(word) for word in words) <= target <= sum(len(word) for word in words)


def check_given_size(size: int, words: list[str], answer: str) -> None:
    for word in words:
        if len(word) > size:
            raise MechanicBuildError(
                f"The word '{word}' has {len(word)} letters, more than the grid size {size}.",
                fix_hint="Use a bigger size or a shorter word.",
            )
    target: int = covered_cell_target(size, answer)
    letter_count: int = sum(len(word) for word in words)
    if target > letter_count:
        raise MechanicBuildError(
            f"In a {size}x{size} grid, the words must cover {target} cells, so that the {len(answer)} cells left over "
            f"spell the answer. The words have only {letter_count} letters.",
            fix_hint="Add words, use longer words, or use a smaller size.",
        )
    if not size_fits(size, words, answer):
        raise MechanicBuildError(
            f"In a {size}x{size} grid, {len(answer)} answer letters leave only {target} cells for words with "
            f"{letter_count} letters.",
            fix_hint="Remove words, use shorter words, use a bigger size, or use a shorter answer.",
        )


def candidate_sizes(params: WordSearchParams, words: list[str], answer: str) -> list[int]:
    """Return the sizes to try, the ones that need the fewest shared letters between words first."""
    if params.size is not None:
        check_given_size(params.size, words, answer)
        return [params.size]
    letter_count: int = sum(len(word) for word in words)
    sizes: list[int] = [size for size in WORD_SEARCH_SIZES if size_fits(size, words, answer)]
    if not sizes:
        raise MechanicBuildError(
            f"No grid size from {min(WORD_SEARCH_SIZES)} to {max(WORD_SEARCH_SIZES)} fits {letter_count} word letters "
            f"and {len(answer)} answer letters.",
            fix_hint="Add words, use longer words, or use a shorter answer.",
        )
    return sorted(sizes, key=lambda size: letter_count - covered_cell_target(size, answer))


def word_cells(start: Cell, step: Step, length: int) -> list[Cell]:
    return [(start[0] + index * step[0], start[1] + index * step[1]) for index in range(length)]


def word_occurrences(grid: LetterGrid, word: str, steps: tuple[Step, ...]) -> list[frozenset[Cell]]:
    """Return every set of cells that spells the word in an allowed direction, in a fixed order."""
    size: int = len(grid)
    found: set[frozenset[Cell]] = set()
    for start in all_cells(size):
        for step in steps:
            cells: list[Cell] = word_cells(start, step, len(word))
            inside: bool = all(0 <= row < size and 0 <= column < size for row, column in cells)
            if inside and all(grid[row][column] == letter for (row, column), letter in zip(cells, word, strict=True)):
                found.add(frozenset(cells))
    return sorted(found, key=sorted)


type Placement = tuple[Cell, ...]


class WordSearchLayout:
    """A depth-first search for word places that leave exactly as many open cells as the answer has letters.

    The open cells must be exactly the answer letters, so the grid is dense. The search keeps, for each word that is
    not placed yet, the list of places that still fit. It places the word with the fewest places first, and it stops a
    branch when a word has no place left or when more cells than the answer letters can no longer get a word.
    """

    def __init__(self, words: list[str], size: int, steps: tuple[Step, ...], answer: str, rng: random.Random) -> None:
        self.words: list[str] = words
        self.size: int = size
        self.steps: tuple[Step, ...] = steps
        self.answer: str = answer
        self.rng: random.Random = rng
        self.letters: dict[Cell, str] = {}
        self.nodes_left: int = WORD_SEARCH_NODE_BUDGET

    def all_placements(self, word: str) -> list[Placement]:
        placements: list[Placement] = []
        for start in all_cells(self.size):
            for step in self.steps:
                cells: list[Cell] = word_cells(start, step, len(word))
                end_row, end_column = cells[-1]
                if 0 <= end_row < self.size and 0 <= end_column < self.size:
                    placements.append(tuple(cells))
        self.rng.shuffle(placements)
        return placements

    def fits(self, placement: Placement, word: str) -> bool:
        """A place fits when its letters agree with the grid and it covers at least one open cell."""
        open_cell_found: bool = False
        for cell, letter in zip(placement, word, strict=True):
            existing: str | None = self.letters.get(cell)
            if existing is None:
                open_cell_found = True
            elif existing != letter:
                return False
        return open_cell_found

    def can_still_finish(self, options: dict[str, list[Placement]]) -> bool:
        open_count: int = self.size * self.size - len(self.letters)
        to_cover: int = open_count - len(self.answer)
        if not len(options) <= to_cover <= sum(len(word) for word in options):
            return False
        reachable: set[Cell] = {
            cell for placements in options.values() for placement in placements for cell in placement
        }
        unreachable_open_count: int = open_count - len(reachable - self.letters.keys())
        return unreachable_open_count <= len(self.answer)

    def finished_grid(self) -> LetterGrid | None:
        if self.size * self.size - len(self.letters) != len(self.answer):
            return None
        free_letters: Iterator[str] = iter(self.answer)
        grid: LetterGrid = [
            [self.letters.get((row, column)) or next(free_letters) for column in range(self.size)]
            for row in range(self.size)
        ]
        unique: bool = all(len(word_occurrences(grid, word, self.steps)) == 1 for word in self.words)
        return grid if unique else None

    def search(self, options: dict[str, list[Placement]] | None = None) -> LetterGrid | None:
        if options is None:
            options = {word: self.all_placements(word) for word in self.words}
        if not options:
            return self.finished_grid()
        if any(not placements for placements in options.values()) or not self.can_still_finish(options):
            return None
        word: str = min(options, key=lambda candidate: (len(options[candidate]), candidate))
        for placement in self.ordered_placements(word, options):
            if self.nodes_left <= 0:
                return None
            self.nodes_left -= 1
            grid: LetterGrid | None = self.try_placement(word, placement, options)
            if grid is not None:
                return grid
        return None

    def ordered_placements(self, word: str, options: dict[str, list[Placement]]) -> list[Placement]:
        """Prefer the places whose count of newly covered cells keeps the search on track to cover the target."""
        to_cover: int = self.size * self.size - len(self.letters) - len(self.answer)
        wanted_new: float = len(word) * to_cover / sum(len(other) for other in options)
        return sorted(
            options[word],
            key=lambda placement: abs(sum(1 for cell in placement if cell not in self.letters) - wanted_new),
        )

    def try_placement(self, word: str, placement: Placement, options: dict[str, list[Placement]]) -> LetterGrid | None:
        new_cells: list[Cell] = [cell for cell in placement if cell not in self.letters]
        self.letters.update(zip(placement, word, strict=True))
        remaining: dict[str, list[Placement]] = {
            other: [candidate for candidate in placements if self.fits(candidate, other)]
            for other, placements in options.items()
            if other != word
        }
        grid: LetterGrid | None = self.search(remaining)
        for cell in new_cells:
            del self.letters[cell]
        return grid


def word_search_grid(sizes: list[int], words: list[str], steps: tuple[Step, ...], answer: str, seed: int) -> LetterGrid:
    rng: random.Random = random.Random(seed)
    for size in sizes:
        for _restart in range(WORD_SEARCH_RESTARTS):
            grid: LetterGrid | None = WordSearchLayout(words, size, steps, answer, rng).search()
            if grid is not None:
                return grid
    target: int = covered_cell_target(sizes[0], answer)
    comfortable_maximum: int = int(target * (1 + COMFORTABLE_SHARED_LETTER_SHARE))
    raise MechanicBuildError(
        "The builder found no layout where the words leave exactly the answer letters.",
        fix_hint=f"Change the words so that they have {target} to {comfortable_maximum} letters in total "
        f"(the {sizes[0]}x{sizes[0]} grid needs {target} covered cells), or change the size.",
    )


def build_word_search(params: WordSearchParams, context: MechanicContext) -> Artifact:
    answer: str = require_answer_letters(context)
    steps: tuple[Step, ...] = STEPS_BY_DIRECTIONS[params.directions]
    words: list[str] = folded_words(params.words)
    reject_nested_words(words, reversed_allowed=params.directions == "hard")
    grid: LetterGrid = word_search_grid(candidate_sizes(params, words, answer), words, steps, answer, context.seed)
    word_list: str = "\n".join(f"<li>{escape(word)}</li>" for word in words)
    return Artifact(
        html=f'<div class="mf-word-search-puzzle">\n{grid_table_html(grid, "mf-word-search")}\n'
        f'<ul class="mf-word-list">\n{word_list}\n</ul>\n</div>',
        solver_text=f"{grid_text(grid)}\n\nWords: {', '.join(words)}",
    )


def decode_word_search(rendered: RenderedArtifact, params: WordSearchParams, context: MechanicContext) -> str:
    """Find each word in the grid read from the page text, then read the cells that no word uses."""
    grid: LetterGrid = single_letter_rows(rendered.text, min(WORD_SEARCH_SIZES))
    steps: tuple[Step, ...] = STEPS_BY_DIRECTIONS[params.directions]
    covered: set[Cell] = set()
    for word in folded_words(params.words):
        for cells in word_occurrences(grid, word, steps)[:1]:
            covered |= cells
    return "".join(grid[row][column] for row, column in all_cells(len(grid)) if (row, column) not in covered)


# grid-coordinates


class GridCoordinatesParams(BaseModel):
    size: int = Field(default=8, ge=5, le=15, description="The number of rows (1, 2, ...) and columns (A, B, ...).")
    coordinates: list[str] | None = Field(
        default=None,
        description='One coordinate per answer letter, such as "C4" (column C, row 4). '
        "Leave it out to let the builder pick the cells.",
    )

    @field_validator("coordinates", mode="before")
    @classmethod
    def split_coordinates(cls, value: object) -> object:
        return split_list_text(value, r"[,\s]+")


def coordinate_name(cell: Cell) -> str:
    return f"{FILL_LETTERS[cell[1]]}{cell[0] + 1}"


def parse_coordinate(code: str, size: int) -> Cell:
    match: re.Match[str] | None = re.fullmatch(r"([A-Z])(\d{1,2})", code.strip().upper())
    if match is None or FILL_LETTERS.index(match[1]) >= size or not 1 <= int(match[2]) <= size:
        raise MechanicBuildError(
            f"The coordinate '{code}' is not a cell of the {size}x{size} grid.",
            fix_hint=f"Write each coordinate as a column letter A to {FILL_LETTERS[size - 1]} and a row number 1 to "
            f"{size}, such as C4.",
        )
    return int(match[2]) - 1, FILL_LETTERS.index(match[1])


def require_grid_room(answer: str, size: int) -> None:
    if len(answer) > size * size:
        raise MechanicBuildError(
            f"The answer has {len(answer)} letters, more than the {size * size} cells of the grid.",
            fix_hint="Use a bigger size.",
        )


def answer_cells(params: GridCoordinatesParams, answer: str, rng: random.Random) -> list[Cell]:
    if params.coordinates is None:
        require_grid_room(answer, params.size)
        return rng.sample(all_cells(params.size), len(answer))
    if len(params.coordinates) != len(answer):
        raise MechanicBuildError(
            f"There are {len(params.coordinates)} coordinates, but the answer '{answer}' has {len(answer)} letters.",
            fix_hint="Give one coordinate per answer letter, or leave out the coordinates.",
        )
    return [parse_coordinate(code, params.size) for code in params.coordinates]


def build_grid_coordinates(params: GridCoordinatesParams, context: MechanicContext) -> Artifact:
    answer: str = require_answer_letters(context)
    rng: random.Random = random.Random(context.seed)
    cells: list[Cell] = answer_cells(params, answer, rng)
    letters_by_cell: dict[Cell, str] = {}
    for cell, letter in zip(cells, answer, strict=True):
        if letters_by_cell.get(cell, letter) != letter:
            raise MechanicBuildError(
                f"The coordinate '{coordinate_name(cell)}' must hold both '{letters_by_cell[cell]}' and '{letter}'.",
                fix_hint="Use a different coordinate for each different letter.",
            )
        letters_by_cell[cell] = letter
    grid: LetterGrid = filled_grid(params.size, letters_by_cell, rng)
    names: list[str] = [coordinate_name(cell) for cell in cells]
    labelled_rows: list[str] = [f"{number} {' '.join(row)}" for number, row in enumerate(grid, start=1)]
    return Artifact(
        html=grid_table_html(grid, "mf-grid-coordinates", f' data-coordinates="{escape(" ".join(names))}"', True),
        solver_text="\n".join(["  " + " ".join(FILL_LETTERS[: params.size]), *labelled_rows])
        + f"\n\nCoordinates: {', '.join(names)}",
    )


def decode_grid_coordinates(rendered: RenderedArtifact, params: GridCoordinatesParams, context: MechanicContext) -> str:
    """Read the labelled rows from the page text and look up each coordinate of the `data-coordinates` attribute."""
    rows: dict[int, list[str]] = {}
    for line in rendered.text.splitlines():
        tokens: list[str] = line.split()
        if len(tokens) == params.size + 1 and tokens[0].isdigit():
            rows[int(tokens[0])] = tokens[1:]
    names: list[str] = re.findall(r'data-coordinates="([^"]*)"', rendered.html)[0].split()
    return "".join(rows[row + 1][column] for row, column in (parse_coordinate(name, params.size) for name in names))


# overlay-mask


class OverlayMaskParams(BaseModel):
    size: int = Field(default=8, ge=4, le=15, description="The number of rows and columns of the grid and the mask.")


def mask_table_html(size: int, holes: list[Cell]) -> str:
    hole_names: str = " ".join(f"{row}-{column}" for row, column in holes)
    lines: list[str] = [f'<table class="mf-mask" data-holes="{hole_names}">']
    for row in range(size):
        cells: list[str] = [
            '<td class="mf-mask-hole"></td>' if (row, column) in holes else "<td></td>" for column in range(size)
        ]
        lines.append("<tr>" + "".join(cells) + "</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def build_overlay_mask(params: OverlayMaskParams, context: MechanicContext) -> Artifact:
    answer: str = require_answer_letters(context)
    require_grid_room(answer, params.size)
    rng: random.Random = random.Random(context.seed)
    holes: list[Cell] = sorted(rng.sample(all_cells(params.size), len(answer)))
    grid: LetterGrid = filled_grid(params.size, dict(zip(holes, answer, strict=True)), rng)
    mask_rows: list[str] = [
        " ".join("#" if (row, column) in holes else "." for column in range(params.size)) for row in range(params.size)
    ]
    return Artifact(
        html=f'<div class="mf-overlay-mask">\n{grid_table_html(grid, "mf-overlay-grid")}\n'
        f"{mask_table_html(params.size, holes)}\n</div>",
        solver_text=f"Grid:\n{grid_text(grid)}\n\nMask (# is a hole):\n" + "\n".join(mask_rows),
        print_notes=("Cut out the pale squares (the windows) of the dark mask card.",),
    )


def decode_overlay_mask(rendered: RenderedArtifact, params: OverlayMaskParams, context: MechanicContext) -> str:
    grid: LetterGrid = single_letter_rows(rendered.text, params.size)
    hole_names: list[str] = re.findall(r'data-holes="([^"]*)"', rendered.html)[0].split()
    holes: list[Cell] = [(int(row), int(column)) for row, column in (name.split("-") for name in hole_names)]
    return "".join(grid[row][column] for row, column in holes)


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(
        id="word-search", params_model=WordSearchParams, build=build_word_search, decode_rendered=decode_word_search
    ),
    MechanicImplementation(
        id="grid-coordinates",
        params_model=GridCoordinatesParams,
        build=build_grid_coordinates,
        decode_rendered=decode_grid_coordinates,
    ),
    MechanicImplementation(
        id="overlay-mask", params_model=OverlayMaskParams, build=build_overlay_mask, decode_rendered=decode_overlay_mask
    ),
)
