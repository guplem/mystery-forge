import html
import itertools
import json
import re
import time
from typing import Any

import pytest

from mystery_forge.mechanics import logic_grid, registry
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
    parse_params,
)

type Row = dict[str, str]

SMALL: dict[str, Any] = {
    "categories": [
        {"name": "Name", "items": ["Ana", "Bruno", "Carla"]},
        {"name": "Drink", "items": ["tea", "coffee", "juice"]},
        {"name": "Job", "items": ["baker", "nurse", "pilot"]},
    ],
    "solution": [
        {"Name": "Ana", "Drink": "coffee", "Job": "pilot"},
        {"Name": "Bruno", "Drink": "tea", "Job": "baker"},
        {"Name": "Carla", "Drink": "juice", "Job": "nurse"},
    ],
    "answer_question": {"category": "Job", "item": "baker", "ask_category": "Drink"},
}

LARGE: dict[str, Any] = {
    "categories": [
        {"name": "House", "items": ["1", "2", "3", "4", "5"]},
        {"name": "Name", "items": ["Ana", "Bruno", "Carla", "Dario", "Elena"]},
        {"name": "Drink", "items": ["tea", "coffee", "juice", "milk", "water"]},
        {"name": "Pet", "items": ["cat", "dog", "fish", "bird", "horse"]},
    ],
    "ordered_category": "House",
    "answer_question": {"category": "Name", "item": "Elena", "ask_category": "Pet"},
}


MEDIUM: dict[str, Any] = {
    "categories": [
        {"name": "House", "items": ["1", "2", "3", "4"]},
        {"name": "Name", "items": ["Ana", "Bruno", "Carla", "Dario"]},
        {"name": "Drink", "items": ["tea", "coffee", "juice", "milk"]},
        {"name": "Pet", "items": ["cat", "dog", "fish", "bird"]},
    ],
    "ordered_category": "House",
    "answer_question": {"category": "Name", "item": "Dario", "ask_category": "Pet"},
}


def make_context(answer: str, seed: int = 2, language: str = "en") -> MechanicContext:
    return MechanicContext(puzzle_id="P1", answer=answer, language=language, seed=seed, documents={})


def implementation() -> MechanicImplementation[Any]:
    return registry.all_implementations()["logic-grid"]


def build(raw_params: dict[str, Any], context: MechanicContext) -> Artifact:
    return implementation().build(parse_params(implementation(), raw_params), context)


def expect_build_error(raw_params: dict[str, Any], context: MechanicContext) -> MechanicBuildError:
    with pytest.raises(MechanicBuildError) as raised:
        build(raw_params, context)
    return raised.value


def structured_clues(artifact: Artifact) -> list[dict[str, Any]]:
    clues: list[dict[str, Any]] = json.loads(html.unescape(re.findall(r'data-clues="([^"]*)"', artifact.html)[0]))
    return clues


def all_solutions(raw_params: dict[str, Any]) -> list[list[Row]]:
    """Every assignment of the items to the entities of the first category, as rows."""
    categories: list[dict[str, Any]] = raw_params["categories"]
    anchor: dict[str, Any] = categories[0]
    solutions: list[list[Row]] = []
    for orders in itertools.product(*(itertools.permutations(category["items"]) for category in categories[1:])):
        solutions.append(
            [
                {
                    anchor["name"]: item,
                    **{category["name"]: order[index] for category, order in zip(categories[1:], orders, strict=True)},
                }
                for index, item in enumerate(anchor["items"])
            ]
        )
    return solutions


def clue_holds(clue: dict[str, Any], rows: list[Row], raw_params: dict[str, Any]) -> bool:
    def row_of(reference: list[str]) -> int:
        return next(index for index, row in enumerate(rows) if row[reference[0]] == reference[1])

    def position(reference: list[str]) -> int:
        ordered: str = raw_params["ordered_category"]
        items: list[str] = next(c["items"] for c in raw_params["categories"] if c["name"] == ordered)
        return items.index(rows[row_of(reference)][ordered])

    references: list[list[str]] = clue["refs"]
    kind: str = clue["kind"]
    if kind == "same":
        return row_of(references[0]) == row_of(references[1])
    if kind == "not_same":
        return row_of(references[0]) != row_of(references[1])
    if kind == "left_of":
        return position(references[0]) + 1 == position(references[1])
    if kind == "next_to":
        return abs(position(references[0]) - position(references[1])) == 1
    assert kind == "either"
    return row_of(references[0]) in (row_of(references[1]), row_of(references[2]))


def matching_solutions(artifact: Artifact, raw_params: dict[str, Any]) -> list[list[Row]]:
    clues: list[dict[str, Any]] = structured_clues(artifact)
    return [rows for rows in all_solutions(raw_params) if all(clue_holds(clue, rows, raw_params) for clue in clues)]


def test_logic_grid_is_registered() -> None:
    assert implementation() in logic_grid.IMPLEMENTATIONS


def test_logic_grid_small_puzzle_has_exactly_the_given_solution() -> None:
    artifact: Artifact = build(SMALL, make_context("Tea"))
    solutions: list[list[Row]] = matching_solutions(artifact, SMALL)
    assert solutions == [SMALL["solution"]]
    clue_items: list[str] = re.findall(r"<li>(.*?)</li>", artifact.html)
    assert len(clue_items) == len(structured_clues(artifact))
    assert "Which Drink goes with baker?" in artifact.html
    assert '<table class="mf-logic-notes">' in artifact.html


def test_logic_grid_clues_are_minimal() -> None:
    artifact: Artifact = build(SMALL, make_context("tea"))
    clues: list[dict[str, Any]] = structured_clues(artifact)
    for left_out in range(len(clues)):
        kept: list[dict[str, Any]] = clues[:left_out] + clues[left_out + 1 :]
        remaining: list[list[Row]] = [
            rows for rows in all_solutions(SMALL) if all(clue_holds(clue, rows, SMALL) for clue in kept)
        ]
        assert len(remaining) > 1


def test_logic_grid_draws_a_random_solution_whose_answer_matches() -> None:
    artifact: Artifact = build(MEDIUM, make_context("Fish", seed=5))
    solutions: list[list[Row]] = matching_solutions(artifact, MEDIUM)
    assert len(solutions) == 1
    dario: Row = next(row for row in solutions[0] if row["Name"] == "Dario")
    assert dario["Pet"] == "fish"
    assert "House order, from left to right: 1, 2, 3, 4." in artifact.html


@pytest.mark.parametrize("seed", range(5))
def test_logic_grid_builds_a_four_by_five_puzzle_quickly(seed: int) -> None:
    started: float = time.perf_counter()
    artifact: Artifact = build(LARGE, make_context("horse", seed=seed))
    assert time.perf_counter() - started < 2
    assert 'data-clues="' in artifact.html


def test_logic_grid_uses_positional_clues_when_a_category_is_ordered() -> None:
    kinds: set[str] = set()
    for seed in range(4):
        kinds |= {clue["kind"] for clue in structured_clues(build(LARGE, make_context("horse", seed=seed)))}
    assert {"left_of", "next_to"} <= kinds
    unordered: dict[str, Any] = {key: value for key, value in LARGE.items() if key != "ordered_category"}
    plain_kinds: set[str] = {clue["kind"] for clue in structured_clues(build(unordered, make_context("horse")))}
    assert not plain_kinds & {"left_of", "next_to"}


def test_logic_grid_can_ask_for_an_item_of_the_first_category() -> None:
    params: dict[str, Any] = {
        **MEDIUM,
        "answer_question": {"category": "Drink", "item": "milk", "ask_category": "House"},
    }
    artifact: Artifact = build(params, make_context("3"))
    solutions: list[list[Row]] = matching_solutions(artifact, params)
    assert len(solutions) == 1
    assert next(row for row in solutions[0] if row["Drink"] == "milk")["House"] == "3"


def test_logic_grid_is_deterministic() -> None:
    assert build(LARGE, make_context("cat", seed=7)) == build(LARGE, make_context("cat", seed=7))


def test_logic_grid_writes_spanish_clues_and_falls_back_to_english() -> None:
    spanish: Artifact = build(SMALL, make_context("tea", language="es"))
    assert "¿Qué Drink va con baker?" in spanish.html
    assert re.search(r"<li>[^<]* (va con|no va con|o con) ", spanish.html)
    french: Artifact = build(SMALL, make_context("tea", language="fr"))
    assert "Which Drink goes with baker?" in french.html


def test_logic_grid_solver_text_lists_categories_clues_and_question() -> None:
    artifact: Artifact = build(LARGE, make_context("horse"))
    assert artifact.solver_text.startswith("House: 1, 2, 3, 4, 5\nName: Ana, Bruno, Carla, Dario, Elena")
    assert "\nClues:\n1. " in artifact.solver_text
    assert artifact.solver_text.endswith("Question: Which Pet goes with Elena?")


@pytest.mark.parametrize(("raw_params", "answer"), [(SMALL, "tea"), (LARGE, "Horse")])
def test_logic_grid_round_trip(raw_params: dict[str, Any], answer: str) -> None:
    context: MechanicContext = make_context(answer)
    artifact: Artifact = build(raw_params, context)
    decoder = implementation().decode_rendered
    assert decoder is not None
    rendered: RenderedArtifact = RenderedArtifact(text=re.sub(r"<[^>]+>", "", artifact.html), html=artifact.html)
    assert decoder(rendered, parse_params(implementation(), raw_params), context).lower() == answer.lower()


CONTRADICTION: str = html.escape(json.dumps([{"kind": "same", "refs": [["Name", "Ana"], ["Name", "Bruno"]]}]))


@pytest.mark.parametrize("clue_text", ["[]", CONTRADICTION])
def test_logic_grid_decode_returns_nothing_without_exactly_one_solution(clue_text: str) -> None:
    context: MechanicContext = make_context("tea")
    artifact: Artifact = build(SMALL, context)
    weakened: str = re.sub(r'data-clues="[^"]*"', f'data-clues="{clue_text}"', artifact.html)
    decoder = implementation().decode_rendered
    assert decoder is not None
    assert decoder(RenderedArtifact(text="", html=weakened), parse_params(implementation(), SMALL), context) == ""


def test_logic_grid_escapes_item_names() -> None:
    params: dict[str, Any] = {
        **SMALL,
        "categories": [*SMALL["categories"][:2], {"name": "Job", "items": ["<script>", "nurse", "pilot"]}],
        "solution": None,
        "answer_question": {"category": "Name", "item": "Ana", "ask_category": "Drink"},
    }
    artifact: Artifact = build(params, make_context("tea"))
    assert "<script" not in artifact.html
    assert "&lt;script&gt;" in artifact.html


def with_changes(base: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return {**base, **changes}


ERROR_CASES: list[tuple[dict[str, Any], str, str, str]] = [
    (
        with_changes(SMALL, categories=[*SMALL["categories"][:2], {"name": "Name", "items": ["x", "y", "z"]}]),
        "tea",
        "The category name 'Name' appears twice.",
        "Give every category a different name.",
    ),
    (
        with_changes(SMALL, categories=[*SMALL["categories"][:2], {"name": "Job", "items": ["x", "y", "z", "w"]}]),
        "tea",
        "Every category needs the same number of items, but 'Name' has 3 and 'Job' has 4.",
        "Give every category the same number of items.",
    ),
    (
        with_changes(SMALL, categories=[*SMALL["categories"][:2], {"name": "Job", "items": ["Téa", "nurse", "pilot"]}]),
        "tea",
        "The item 'Téa' appears twice (also across categories, and accents do not count).",
        "Give every item a different name.",
    ),
    (
        with_changes(SMALL, ordered_category="Age"),
        "tea",
        "The ordered category 'Age' is not a category.",
        "Use one of these category names: Name, Drink, Job.",
    ),
    (
        with_changes(SMALL, answer_question={"category": "Age", "item": "x", "ask_category": "Drink"}),
        "tea",
        "The question category 'Age' is not a category.",
        "Use one of these category names: Name, Drink, Job.",
    ),
    (
        with_changes(SMALL, answer_question={"category": "Job", "item": "baker", "ask_category": "Age"}),
        "tea",
        "The question category 'Age' is not a category.",
        "Use one of these category names: Name, Drink, Job.",
    ),
    (
        with_changes(SMALL, answer_question={"category": "Job", "item": "chef", "ask_category": "Drink"}),
        "tea",
        "The question item 'chef' is not in the category 'Job'.",
        "Use one of these items: baker, nurse, pilot.",
    ),
    (
        with_changes(SMALL, answer_question={"category": "Job", "item": "baker", "ask_category": "Job"}),
        "tea",
        "The question asks for the category 'Job' of an item of that same category.",
        "Ask for a different category.",
    ),
    (
        with_changes(SMALL, solution=SMALL["solution"][:2]),
        "tea",
        "The solution has 2 rows, but each category has 3 items.",
        "Give one solution row per item.",
    ),
    (
        with_changes(SMALL, solution=[*SMALL["solution"][:2], {"Name": "Carla", "Drink": "juice"}]),
        "tea",
        "Solution row 3 has no item of the category 'Job'.",
        "Give each solution row one item of every category.",
    ),
    (
        with_changes(SMALL, solution=[*SMALL["solution"][:2], {"Name": "Carla", "Drink": "soda", "Job": "nurse"}]),
        "tea",
        "Solution row 3 gives 'soda', which is not an item of the category 'Drink'.",
        "Use one of these items: tea, coffee, juice.",
    ),
    (
        with_changes(SMALL, solution=[*SMALL["solution"][:2], {"Name": "Carla", "Drink": "tea", "Job": "nurse"}]),
        "tea",
        "The item 'tea' appears in more than one solution row.",
        "Use each item in exactly one solution row.",
    ),
    (
        SMALL,
        "coffee",
        "The solution answers the question with 'tea', not with the answer 'coffee'.",
        "Change the solution or the answer so that they agree.",
    ),
    (
        with_changes(SMALL, solution=None),
        "soda",
        "The answer 'soda' is not an item of the category 'Drink'.",
        "Make the answer one of the items of the category 'Drink'.",
    ),
]


@pytest.mark.parametrize(("raw_params", "answer", "message", "fix_hint"), ERROR_CASES)
def test_logic_grid_rejects_invalid_params(
    raw_params: dict[str, Any], answer: str, message: str, fix_hint: str
) -> None:
    error: MechanicBuildError = expect_build_error(raw_params, make_context(answer))
    assert error.message == message
    assert error.fix_hint == fix_hint


def test_logic_grid_rejects_a_bad_category_count() -> None:
    with pytest.raises(MechanicBuildError):
        parse_params(implementation(), with_changes(SMALL, categories=SMALL["categories"][:2]))
