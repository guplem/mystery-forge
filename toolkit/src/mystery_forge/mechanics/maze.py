"""The maze mechanic: a perfect maze whose one path from the entrance to the exit passes the answer letters in order.

A seeded recursive backtracker carves the maze, so every two cells have exactly one path between them. The SVG keeps
the walls in a `data-walls` attribute (one hex digit per cell) and every letter in a `<text>` element, so the decoder
solves the maze again from what the page shows.
"""

import random
import re
import string
from collections import deque
from typing import Any

from pydantic import BaseModel, Field

from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)

type Cell = tuple[int, int]
type Walls = list[list[int]]

NORTH: int = 1
EAST: int = 2
SOUTH: int = 4
WEST: int = 8
ALL_WALLS: int = NORTH | EAST | SOUTH | WEST
# Each move: the wall that it crosses, the row step, the column step, and the wall on the other side.
MOVES: tuple[tuple[int, int, int, int], ...] = (
    (NORTH, -1, 0, SOUTH),
    (EAST, 0, 1, WEST),
    (SOUTH, 1, 0, NORTH),
    (WEST, 0, -1, EAST),
)
MAZE_ATTEMPTS: int = 20
CELL_PIXELS: int = 24
MARGIN_PIXELS: int = 16
FILL_LETTERS: str = string.ascii_uppercase


class MazeParams(BaseModel):
    size: int = Field(default=10, ge=6, le=20, description="The number of rows and columns of the maze.")
    distractors: bool = Field(
        default=True, description="Put random letters in some cells off the path, so a player must solve the maze."
    )


def carved_maze(size: int, rng: random.Random) -> Walls:
    """Carve a perfect maze with an iterative recursive backtracker, then open the entrance and the exit."""
    walls: Walls = [[ALL_WALLS] * size for _row in range(size)]
    visited: set[Cell] = {(0, 0)}
    stack: list[Cell] = [(0, 0)]
    while stack:
        row, column = stack[-1]
        moves: list[tuple[int, int, int, int]] = [
            move
            for move in MOVES
            if 0 <= row + move[1] < size
            and 0 <= column + move[2] < size
            and (row + move[1], column + move[2]) not in visited
        ]
        if not moves:
            stack.pop()
            continue
        wall, row_step, column_step, opposite = rng.choice(moves)
        target: Cell = (row + row_step, column + column_step)
        walls[row][column] &= ~wall
        walls[target[0]][target[1]] &= ~opposite
        visited.add(target)
        stack.append(target)
    walls[0][0] &= ~NORTH
    walls[size - 1][size - 1] &= ~SOUTH
    return walls


def solution_path(walls: Walls) -> list[Cell]:
    """Return the path from the top-left entrance to the bottom-right exit. A perfect maze has exactly one."""
    size: int = len(walls)
    previous: dict[Cell, Cell | None] = {(0, 0): None}
    queue: deque[Cell] = deque([(0, 0)])
    while queue:
        row, column = queue.popleft()
        for wall, row_step, column_step, _opposite in MOVES:
            target: Cell = (row + row_step, column + column_step)
            inside: bool = 0 <= target[0] < size and 0 <= target[1] < size
            if inside and not walls[row][column] & wall and target not in previous:
                previous[target] = (row, column)
                queue.append(target)
    path: list[Cell] = []
    current: Cell | None = (size - 1, size - 1)
    while current is not None:
        path.append(current)
        current = previous[current]
    return path[::-1]


def maze_with_long_enough_path(size: int, answer: str, rng: random.Random) -> tuple[Walls, list[Cell]]:
    longest: int = 0
    for _attempt in range(MAZE_ATTEMPTS):
        walls: Walls = carved_maze(size, rng)
        path: list[Cell] = solution_path(walls)
        if len(path) >= len(answer):
            return walls, path
        longest = max(longest, len(path))
    raise MechanicBuildError(
        f"The answer has {len(answer)} letters, but the longest path that the builder found has {longest} cells.",
        fix_hint="Use a bigger size or a shorter answer.",
    )


def maze_letters(path: list[Cell], answer: str, size: int, distractors: bool, rng: random.Random) -> dict[Cell, str]:
    """Spread the answer letters evenly along the path, and put distractor letters only off the path."""
    letters: dict[Cell, str] = {
        path[(2 * index + 1) * len(path) // (2 * len(answer))]: letter for index, letter in enumerate(answer)
    }
    if distractors:
        on_path: set[Cell] = set(path)
        off_path: list[Cell] = [
            (row, column) for row in range(size) for column in range(size) if (row, column) not in on_path
        ]
        distractor_count: int = min(len(off_path), round(len(answer) * len(off_path) / len(path)))
        for cell in rng.sample(off_path, distractor_count):
            letters[cell] = rng.choice(FILL_LETTERS)
    return letters


def wall_lines(walls: Walls) -> list[tuple[int, int, int, int]]:
    """Return the wall segments in cell units: each cell draws its north and west walls, the border cells the rest."""
    size: int = len(walls)
    lines: list[tuple[int, int, int, int]] = []
    for row in range(size):
        for column in range(size):
            if walls[row][column] & NORTH:
                lines.append((column, row, column + 1, row))
            if walls[row][column] & WEST:
                lines.append((column, row, column, row + 1))
            if column == size - 1 and walls[row][column] & EAST:
                lines.append((column + 1, row, column + 1, row + 1))
            if row == size - 1 and walls[row][column] & SOUTH:
                lines.append((column, row + 1, column + 1, row + 1))
    return lines


def pixel(units: float) -> str:
    return f"{MARGIN_PIXELS + units * CELL_PIXELS:g}"


def maze_svg(walls: Walls, letters: dict[Cell, str]) -> str:
    size: int = len(walls)
    side: int = 2 * MARGIN_PIXELS + size * CELL_PIXELS
    wall_text: str = "".join(f"{walls[row][column]:x}" for row in range(size) for column in range(size))
    segments: str = "".join(
        f'<line x1="{pixel(x1)}" y1="{pixel(y1)}" x2="{pixel(x2)}" y2="{pixel(y2)}"/>'
        for x1, y1, x2, y2 in wall_lines(walls)
    )
    texts: str = "".join(
        f'<text class="mf-maze-letter" x="{pixel(column + 0.5)}" y="{pixel(row + 0.5)}" data-cell="{row}-{column}" '
        f'text-anchor="middle" dominant-baseline="central" fill="currentColor">{letter}</text>'
        for (row, column), letter in sorted(letters.items())
    )
    arrows: str = "".join(
        f'<path class="mf-maze-arrow" d="M{pixel(column + 0.3)} {pixel(top)} L{pixel(column + 0.7)} {pixel(top)} '
        f'L{pixel(column + 0.5)} {pixel(top + 0.4)} Z" fill="currentColor"/>'
        for column, top in ((0, -0.55), (size - 1, size + 0.1))
    )
    return (
        f'<svg class="mf-maze" viewBox="0 0 {side} {side}" role="img" aria-label="Maze" data-size="{size}" '
        f'data-walls="{wall_text}"><g class="mf-maze-walls" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="square">{segments}</g>{texts}{arrows}</svg>'
    )


def maze_ascii(walls: Walls, letters: dict[Cell, str]) -> list[str]:
    size: int = len(walls)
    lines: list[str] = ["+" + "".join("---+" if walls[0][column] & NORTH else "   +" for column in range(size))]
    for row in range(size):
        cells: str = "".join(
            ("|" if walls[row][column] & WEST else " ") + f" {letters.get((row, column), ' ')} "
            for column in range(size)
        )
        lines.append(cells + ("|" if walls[row][size - 1] & EAST else " "))
        lines.append("+" + "".join("---+" if walls[row][column] & SOUTH else "   +" for column in range(size)))
    return lines


def build_maze(params: MazeParams, context: MechanicContext) -> Artifact:
    if not context.normalized_answer:
        raise MechanicBuildError(
            "The answer has no letters or digits.",
            fix_hint="Give the puzzle an answer with at least one letter or digit.",
        )
    answer: str = context.normalized_answer.upper()
    rng: random.Random = random.Random(context.seed)
    walls, path = maze_with_long_enough_path(params.size, answer, rng)
    letters: dict[Cell, str] = maze_letters(path, answer, params.size, params.distractors, rng)
    return Artifact(
        html=maze_svg(walls, letters),
        solver_text="\n".join(["  v", *maze_ascii(walls, letters), " " * (4 * (params.size - 1) + 2) + "v"]),
    )


def decode_maze(rendered: RenderedArtifact, params: MazeParams, context: MechanicContext) -> str:
    """Solve the maze from the drawn walls and read the letters along the path."""
    size: int = int(re.findall(r'data-size="(\d+)"', rendered.html)[0])
    wall_text: str = re.findall(r'data-walls="([0-9a-f]+)"', rendered.html)[0]
    walls: Walls = [[int(wall_text[row * size + column], 16) for column in range(size)] for row in range(size)]
    letters: dict[Cell, str] = {
        (int(row), int(column)): letter
        for row, column, letter in re.findall(r'<text[^>]*data-cell="(\d+)-(\d+)"[^>]*>([^<]*)</text>', rendered.html)
    }
    return "".join(letters[cell] for cell in solution_path(walls) if cell in letters)


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(id="maze", params_model=MazeParams, build=build_maze, decode_rendered=decode_maze),
)
