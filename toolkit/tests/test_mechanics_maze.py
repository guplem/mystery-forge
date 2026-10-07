import html
import re
from collections import deque
from typing import Any

import pytest

from mystery_forge.mechanics import maze, registry
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)

type Cell = tuple[int, int]

# Wall bits as the builder stores them in `data-walls`: north 1, east 2, south 4, west 8.
MOVES: tuple[tuple[int, int, int], ...] = ((1, -1, 0), (2, 0, 1), (4, 1, 0), (8, 0, -1))


def make_context(answer: str, seed: int = 21) -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language="en", seed=seed, documents={})


def implementation() -> MechanicImplementation[Any]:
    return registry.all_implementations()["maze"]


def build(raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    return implementation().build(parse_params(implementation(), raw_params), context)


def parsed_maze(artifact: Artifact) -> tuple[int, list[list[int]], dict[Cell, str]]:
    size: int = int(re.findall(r'data-size="(\d+)"', artifact.html)[0])
    wall_text: str = re.findall(r'data-walls="([0-9a-f]+)"', artifact.html)[0]
    walls: list[list[int]] = [
        [int(wall_text[row * size + column], 16) for column in range(size)] for row in range(size)
    ]
    letters: dict[Cell, str] = {
        (int(row), int(column)): letter
        for row, column, letter in re.findall(r'<text[^>]*data-cell="(\d+)-(\d+)"[^>]*>([^<]*)</text>', artifact.html)
    }
    return size, walls, letters


def neighbours(walls: list[list[int]], cell: Cell) -> list[Cell]:
    size: int = len(walls)
    row, column = cell
    found: list[Cell] = []
    for bit, row_step, column_step in MOVES:
        target: Cell = (row + row_step, column + column_step)
        if not walls[row][column] & bit and 0 <= target[0] < size and 0 <= target[1] < size:
            found.append(target)
    return found


def shortest_path(walls: list[list[int]]) -> list[Cell]:
    size: int = len(walls)
    previous: dict[Cell, Cell | None] = {(0, 0): None}
    queue: deque[Cell] = deque([(0, 0)])
    while queue:
        cell: Cell = queue.popleft()
        for target in neighbours(walls, cell):
            if target not in previous:
                previous[target] = cell
                queue.append(target)
    path: list[Cell] = []
    current: Cell | None = (size - 1, size - 1)
    while current is not None:
        path.append(current)
        current = previous[current]
    return path[::-1]


def count_simple_paths(walls: list[list[int]], cell: Cell, goal: Cell, seen: set[Cell]) -> int:
    if cell == goal:
        return 1
    total: int = 0
    for target in neighbours(walls, cell):
        if target not in seen:
            total += count_simple_paths(walls, target, goal, seen | {target})
    return total


def test_maze_is_registered() -> None:
    assert implementation() in maze.IMPLEMENTATIONS


def test_maze_is_a_perfect_maze_whose_path_letters_spell_the_answer() -> None:
    artifact: Artifact = build({"size": "8"}, make_context("Faro"))
    size, walls, letters = parsed_maze(artifact)
    assert size == 8
    passages: int = sum(len(neighbours(walls, (row, column))) for row in range(size) for column in range(size)) // 2
    assert passages == size * size - 1
    path: list[Cell] = shortest_path(walls)
    assert count_simple_paths(walls, (0, 0), (size - 1, size - 1), {(0, 0)}) == 1
    assert "".join(letters[cell] for cell in path if cell in letters) == "FARO"
    off_path: set[Cell] = set(letters) - set(path)
    assert off_path
    assert walls[0][0] & 1 == 0
    assert walls[size - 1][size - 1] & 4 == 0


def test_maze_every_cell_is_reachable() -> None:
    artifact: Artifact = build({"size": 6}, make_context("key"))
    _size, walls, _letters = parsed_maze(artifact)
    reached: set[Cell] = {(0, 0)}
    queue: deque[Cell] = deque([(0, 0)])
    while queue:
        for target in neighbours(walls, queue.popleft()):
            if target not in reached:
                reached.add(target)
                queue.append(target)
    assert len(reached) == 36


def test_maze_spaces_the_answer_letters_along_the_path() -> None:
    artifact: Artifact = build({"size": 10, "distractors": "false"}, make_context("ab"))
    _size, walls, letters = parsed_maze(artifact)
    path: list[Cell] = shortest_path(walls)
    positions: list[int] = [index for index, cell in enumerate(path) if cell in letters]
    assert len(letters) == 2
    assert positions == [len(path) // 4, (3 * len(path)) // 4]


def test_maze_svg_is_safe_and_uses_the_current_color() -> None:
    artifact: Artifact = build({}, make_context("Room 7"))
    assert artifact.html.startswith('<svg class="mf-maze"')
    assert 'stroke="currentColor"' in artifact.html
    assert "<script" not in artifact.html
    assert "href" not in artifact.html
    assert "#" not in artifact.html
    assert re.findall(r'data-size="(\d+)"', artifact.html) == ["10"]


def test_maze_solver_text_draws_the_maze_in_ascii() -> None:
    artifact: Artifact = build({"size": 6}, make_context("key"))
    lines: list[str] = artifact.solver_text.splitlines()
    # The arrows of the printed maze, above the entry and below the exit: no words, so no language.
    assert lines[0] == "  v"
    assert lines[1].startswith("+   +")
    assert len(lines) == 1 + 2 * 6 + 1 + 1
    assert lines[-2].endswith("+   +")
    assert lines[-1] == " " * (4 * 5 + 2) + "v"
    assert all(letter in artifact.solver_text for letter in "KEY")


def test_maze_is_deterministic_and_depends_on_the_seed() -> None:
    assert build({}, make_context("key", seed=3)) == build({}, make_context("key", seed=3))
    assert build({}, make_context("key", seed=3)) != build({}, make_context("key", seed=4))


@pytest.mark.parametrize("distractors", [True, False])
def test_maze_round_trip(distractors: bool) -> None:
    context: MechanicContext = make_context("Lighthouse")
    artifact: Artifact = build({"distractors": distractors}, context)
    rendered: RenderedArtifact = RenderedArtifact(
        text=html.unescape(re.sub(r"<[^>]+>", "", artifact.html)), html=artifact.html
    )
    decode = implementation().decode_rendered
    assert decode is not None
    assert decode(rendered, parse_params(implementation(), {"distractors": distractors}), context) == "LIGHTHOUSE"


def test_maze_rejects_an_answer_longer_than_the_path() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        build({"size": 6}, make_context("a" * 37))
    assert re.fullmatch(
        r"The answer has 37 letters, but the longest path that the builder found has \d+ cells\.", raised.value.message
    )
    assert raised.value.fix_hint == "Use a bigger size or a shorter answer."


def test_maze_rejects_an_answer_without_letters() -> None:
    with pytest.raises(MechanicBuildError) as raised:
        build({}, make_context("..."))
    assert raised.value.message == "The answer has no letters or digits."


def test_maze_rejects_a_size_out_of_range() -> None:
    with pytest.raises(MechanicBuildError):
        parse_params(implementation(), {"size": "21"})
