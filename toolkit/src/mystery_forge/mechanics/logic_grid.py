"""The logic-grid mechanic: an Einstein-style puzzle whose clues allow exactly one solution.

Each category (names, drinks, jobs, ...) assigns one item to each item of the first category, the anchor. The builder
takes or draws a solution, writes every true clue that its templates allow, and then removes clues while a small
solver still finds exactly one solution. The page keeps the structured clues in a `data-clues` attribute, so the
decoder solves the rendered puzzle again and answers the question.
"""

import html
import itertools
import json
import random
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from markupsafe import escape
from pydantic import BaseModel, Field

from mystery_forge.answers import normalize_answer
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)

type ItemRef = tuple[int, int]
type Permutation = tuple[int, ...]
# For each category, the item index of each entity. The anchor category maps each entity to itself.
type Assignment = list[Permutation]

POSITIONAL_KINDS: frozenset[str] = frozenset({"left_of", "next_to"})
# The builder starts from every "same" clue plus this many other true clues, then removes all clues it can.
OTHER_CLUE_SAMPLE: int = 40

CLUE_TEMPLATES: dict[str, dict[str, str]] = {
    "en": {
        "same": "{x} goes with {y}.",
        "not_same": "{x} does not go with {y}.",
        "left_of": "{x} is directly left of {y}.",
        "next_to": "{x} is next to {y}.",
        "either": "{z} goes with either {x} or {y}.",
        "question": "Which {category} goes with {item}?",
        "order": "{category} order, from left to right: {items}.",
    },
    "es": {
        "same": "{x} va con {y}.",
        "not_same": "{x} no va con {y}.",
        "left_of": "{x} está justo a la izquierda de {y}.",
        "next_to": "{x} está al lado de {y}.",
        "either": "{z} va con {x} o con {y}.",
        "question": "¿Qué {category} va con {item}?",
        "order": "Orden de {category}, de izquierda a derecha: {items}.",
    },
}


class LogicCategory(BaseModel):
    name: str = Field(description="The category name, such as 'Drink'.")
    items: list[str] = Field(min_length=3, max_length=5, description="The items of the category, 3 to 5.")


class LogicQuestion(BaseModel):
    category: str = Field(description="The category of the item that the question names.")
    item: str = Field(description="The item that the question names, such as 'baker'.")
    ask_category: str = Field(description="The category that the question asks for. Its answer is the puzzle answer.")


class LogicGridParams(BaseModel):
    categories: list[LogicCategory] = Field(
        min_length=3,
        max_length=4,
        description="3 or 4 categories with the same number of items. The first category is the anchor.",
    )
    solution: list[dict[str, str]] | None = Field(
        default=None,
        description="One row per anchor item, mapping each category name to its item. Leave it out to let the "
        "builder draw a solution that gives the answer.",
    )
    answer_question: LogicQuestion = Field(description="The question whose answer in the solution is the answer.")
    ordered_category: str | None = Field(
        default=None,
        description="A category whose items stand in a row from left to right, such as house numbers. "
        "It allows 'left of' and 'next to' clues.",
    )


@dataclass(frozen=True)
class LogicClue:
    kind: str
    # same, not_same, left_of, next_to: (x, y). either: (z, x, y), where x and y share a category.
    refs: tuple[ItemRef, ...]


@dataclass(frozen=True)
class LogicPuzzle:
    names: tuple[str, ...]
    items: tuple[tuple[str, ...], ...]
    ordered: int | None
    question_category: int
    question_item: int
    ask_category: int


# Solver


@cache
def permutations_with_inverses(count: int) -> tuple[tuple[Permutation, Permutation], ...]:
    pairs: list[tuple[Permutation, Permutation]] = []
    for permutation in itertools.permutations(range(count)):
        inverse: list[int] = [0] * count
        for entity, item in enumerate(permutation):
            inverse[item] = entity
        pairs.append((permutation, tuple(inverse)))
    return tuple(pairs)


def clue_categories(clue: LogicClue, ordered: int | None) -> set[int]:
    categories: set[int] = {category for category, _item in clue.refs}
    if clue.kind in POSITIONAL_KINDS and ordered is not None:
        categories.add(ordered)
    return categories


def clue_holds(
    clue: LogicClue, permutations: Mapping[int, Permutation], inverses: Mapping[int, Permutation], ordered: int | None
) -> bool:
    entities: list[int] = [inverses[category][item] for category, item in clue.refs]
    if clue.kind == "same":
        return entities[0] == entities[1]
    if clue.kind == "not_same":
        return entities[0] != entities[1]
    if clue.kind == "either":
        return entities[0] in (entities[1], entities[2])
    assert ordered is not None
    first, second = (permutations[ordered][entity] for entity in entities)
    if clue.kind == "left_of":
        return first + 1 == second
    return abs(first - second) == 1


class LogicSolver:
    """A search over one permutation per category, with forward checking.

    After the search fixes a category, it removes from every other category the permutations that break a clue
    between them, and it fixes next the category with the fewest permutations left. A clue joins the check as soon as
    all of its categories have values, so a near-minimal clue set still prunes early.
    """

    def __init__(self, puzzle: LogicPuzzle, clues: list[LogicClue]) -> None:
        self.puzzle: LogicPuzzle = puzzle
        self.clues: list[tuple[LogicClue, frozenset[int]]] = [
            (clue, frozenset(clue_categories(clue, puzzle.ordered))) for clue in clues
        ]
        identity: Permutation = tuple(range(len(puzzle.items[0])))
        self.permutations: dict[int, Permutation] = {0: identity}
        self.inverses: dict[int, Permutation] = {0: identity}
        self.found: list[Assignment] = []

    def consistent(self, category: int, pair: tuple[Permutation, Permutation], partner: int) -> bool:
        """Check the clues that the category completes and that also involve the partner category."""
        self.permutations[category], self.inverses[category] = pair
        known: set[int] = set(self.permutations)
        holds: bool = all(
            clue_holds(clue, self.permutations, self.inverses, self.puzzle.ordered)
            for clue, categories in self.clues
            if category in categories and partner in categories and categories <= known
        )
        del self.permutations[category], self.inverses[category]
        return holds

    def solutions(self, limit: int) -> list[Assignment]:
        anchor_clues_hold: bool = all(
            clue_holds(clue, self.permutations, self.inverses, self.puzzle.ordered)
            for clue, categories in self.clues
            if categories == {0}
        )
        if anchor_clues_hold:
            every_pair: tuple[tuple[Permutation, Permutation], ...] = permutations_with_inverses(
                len(self.puzzle.items[0])
            )
            domains: dict[int, list[tuple[Permutation, Permutation]]] = {
                category: [pair for pair in every_pair if self.consistent(category, pair, partner=category)]
                for category in range(1, len(self.puzzle.names))
            }
            self.search(domains, limit)
        return self.found

    def search(self, domains: dict[int, list[tuple[Permutation, Permutation]]], limit: int) -> None:
        if not domains:
            self.found.append([self.permutations[category] for category in range(len(self.puzzle.names))])
            return
        category: int = min(domains, key=lambda candidate: (len(domains[candidate]), candidate))
        for pair in domains[category]:
            self.permutations[category], self.inverses[category] = pair
            remaining: dict[int, list[tuple[Permutation, Permutation]]] = {
                other: [option for option in options if self.consistent(other, option, partner=category)]
                for other, options in domains.items()
                if other != category
            }
            if all(remaining.values()):
                self.search(remaining, limit)
            del self.permutations[category], self.inverses[category]
            if len(self.found) >= limit:
                return


def has_one_solution(puzzle: LogicPuzzle, clues: list[LogicClue]) -> bool:
    return len(LogicSolver(puzzle, clues).solutions(limit=2)) == 1


# Params


def category_index(puzzle_names: list[str], name: str, role: str) -> int:
    if name not in puzzle_names:
        raise MechanicBuildError(
            f"The {role} category '{name}' is not a category.",
            fix_hint=f"Use one of these category names: {', '.join(puzzle_names)}.",
        )
    return puzzle_names.index(name)


def check_categories(categories: list[LogicCategory]) -> None:
    names: list[str] = [category.name for category in categories]
    for name in names:
        if names.count(name) > 1:
            raise MechanicBuildError(
                f"The category name '{name}' appears twice.", fix_hint="Give every category a different name."
            )
    for category in categories[1:]:
        if len(category.items) != len(categories[0].items):
            raise MechanicBuildError(
                f"Every category needs the same number of items, but '{categories[0].name}' has "
                f"{len(categories[0].items)} and '{category.name}' has {len(category.items)}.",
                fix_hint="Give every category the same number of items.",
            )
    seen: set[str] = set()
    for item in (item for category in categories for item in category.items):
        if normalize_answer(item, "") in seen:
            raise MechanicBuildError(
                f"The item '{item}' appears twice (also across categories, and accents do not count).",
                fix_hint="Give every item a different name.",
            )
        seen.add(normalize_answer(item, ""))


def logic_puzzle(params: LogicGridParams) -> LogicPuzzle:
    check_categories(params.categories)
    names: list[str] = [category.name for category in params.categories]
    question: LogicQuestion = params.answer_question
    question_category: int = category_index(names, question.category, "question")
    ask_category: int = category_index(names, question.ask_category, "question")
    question_items: list[str] = params.categories[question_category].items
    if question.item not in question_items:
        raise MechanicBuildError(
            f"The question item '{question.item}' is not in the category '{question.category}'.",
            fix_hint=f"Use one of these items: {', '.join(question_items)}.",
        )
    if ask_category == question_category:
        raise MechanicBuildError(
            f"The question asks for the category '{question.category}' of an item of that same category.",
            fix_hint="Ask for a different category.",
        )
    return LogicPuzzle(
        names=tuple(names),
        items=tuple(tuple(category.items) for category in params.categories),
        ordered=None if params.ordered_category is None else category_index(names, params.ordered_category, "ordered"),
        question_category=question_category,
        question_item=question_items.index(question.item),
        ask_category=ask_category,
    )


def given_solution(puzzle: LogicPuzzle, rows: list[dict[str, str]]) -> Assignment:
    item_count: int = len(puzzle.items[0])
    if len(rows) != item_count:
        raise MechanicBuildError(
            f"The solution has {len(rows)} rows, but each category has {item_count} items.",
            fix_hint="Give one solution row per item.",
        )
    columns: list[list[int]] = [[-1] * item_count for _name in puzzle.names]
    for row_number, row in enumerate(rows, start=1):
        indexes: list[int] = [
            solution_item_index(puzzle, category, row, row_number) for category in range(len(puzzle.names))
        ]
        for category, index in enumerate(indexes):
            if index in columns[category]:
                raise MechanicBuildError(
                    f"The item '{puzzle.items[category][index]}' appears in more than one solution row.",
                    fix_hint="Use each item in exactly one solution row.",
                )
            columns[category][indexes[0]] = index
    return [tuple(column) for column in columns]


def solution_item_index(puzzle: LogicPuzzle, category: int, row: dict[str, str], row_number: int) -> int:
    name: str = puzzle.names[category]
    if name not in row:
        raise MechanicBuildError(
            f"Solution row {row_number} has no item of the category '{name}'.",
            fix_hint="Give each solution row one item of every category.",
        )
    if row[name] not in puzzle.items[category]:
        raise MechanicBuildError(
            f"Solution row {row_number} gives '{row[name]}', which is not an item of the category '{name}'.",
            fix_hint=f"Use one of these items: {', '.join(puzzle.items[category])}.",
        )
    return puzzle.items[category].index(row[name])


def entity_of(assignment: Assignment, reference: ItemRef) -> int:
    return assignment[reference[0]].index(reference[1])


def asked_item(puzzle: LogicPuzzle, assignment: Assignment) -> str:
    entity: int = entity_of(assignment, (puzzle.question_category, puzzle.question_item))
    return puzzle.items[puzzle.ask_category][assignment[puzzle.ask_category][entity]]


def swapped(permutation: Permutation, first: int, second: int) -> Permutation:
    values: list[int] = list(permutation)
    values[first], values[second] = values[second], values[first]
    return tuple(values)


def drawn_solution(puzzle: LogicPuzzle, context: MechanicContext, rng: random.Random) -> Assignment:
    """Draw a random solution, then swap two items so that the question gets the answer."""
    ask_items: tuple[str, ...] = puzzle.items[puzzle.ask_category]
    folded_items: list[str] = [normalize_answer(item, context.language) for item in ask_items]
    if context.normalized_answer not in folded_items:
        name: str = puzzle.names[puzzle.ask_category]
        raise MechanicBuildError(
            f"The answer '{context.answer}' is not an item of the category '{name}'.",
            fix_hint=f"Make the answer one of the items of the category '{name}'.",
        )
    answer_item: int = folded_items.index(context.normalized_answer)
    item_count: int = len(puzzle.items[0])
    assignment: Assignment = [tuple(range(item_count))]
    for _category in puzzle.names[1:]:
        values: list[int] = list(range(item_count))
        rng.shuffle(values)
        assignment.append(tuple(values))
    asked_entity: int = entity_of(assignment, (puzzle.question_category, puzzle.question_item))
    if puzzle.ask_category == 0:
        # The anchor maps each entity to itself, so move the question item to the entity of the answer instead.
        holder: int = asked_entity
        moved: int = puzzle.question_category
        assignment[moved] = swapped(assignment[moved], holder, answer_item)
    else:
        holder = entity_of(assignment, (puzzle.ask_category, answer_item))
        assignment[puzzle.ask_category] = swapped(assignment[puzzle.ask_category], asked_entity, holder)
    return assignment


def chosen_solution(
    params: LogicGridParams, puzzle: LogicPuzzle, context: MechanicContext, rng: random.Random
) -> Assignment:
    if params.solution is None:
        return drawn_solution(puzzle, context, rng)
    assignment: Assignment = given_solution(puzzle, params.solution)
    answer: str = asked_item(puzzle, assignment)
    if normalize_answer(answer, context.language) != context.normalized_answer:
        raise MechanicBuildError(
            f"The solution answers the question with '{answer}', not with the answer '{context.answer}'.",
            fix_hint="Change the solution or the answer so that they agree.",
        )
    return assignment


# Clues


def same_clues(puzzle: LogicPuzzle, assignment: Assignment) -> list[LogicClue]:
    return [
        LogicClue("same", ((first, assignment[first][entity]), (second, assignment[second][entity])))
        for first, second in itertools.combinations(range(len(puzzle.names)), 2)
        for entity in range(len(puzzle.items[0]))
    ]


def other_true_clues(puzzle: LogicPuzzle, assignment: Assignment, rng: random.Random) -> list[LogicClue]:
    """Return every true clue that is not a "same" clue."""
    category_count: int = len(puzzle.names)
    entities: range = range(len(puzzle.items[0]))
    clues: list[LogicClue] = [
        LogicClue("not_same", ((first, assignment[first][one]), (second, assignment[second][other])))
        for first, second in itertools.combinations(range(category_count), 2)
        for one in entities
        for other in entities
        if one != other
    ]
    for category in range(category_count):
        for entity in entities:
            for pair_category in range(category_count):
                for other in entities:
                    if pair_category == category or other == entity:
                        continue
                    pair: list[ItemRef] = [
                        (pair_category, assignment[pair_category][entity]),
                        (pair_category, assignment[pair_category][other]),
                    ]
                    rng.shuffle(pair)
                    clues.append(LogicClue("either", ((category, assignment[category][entity]), *pair)))
    if puzzle.ordered is not None:
        clues += positional_clues(puzzle, assignment, puzzle.ordered, rng)
    return clues


def positional_clues(puzzle: LogicPuzzle, assignment: Assignment, ordered: int, rng: random.Random) -> list[LogicClue]:
    clues: list[LogicClue] = []
    for position in range(len(puzzle.items[0]) - 1):
        left: int = entity_of(assignment, (ordered, position))
        right: int = entity_of(assignment, (ordered, position + 1))
        for first, second in itertools.product(range(len(puzzle.names)), repeat=2):
            if first == ordered and second == ordered:
                continue
            x: ItemRef = (first, assignment[first][left])
            y: ItemRef = (second, assignment[second][right])
            clues.append(LogicClue("left_of", (x, y)))
            clues.append(LogicClue("next_to", (x, y) if rng.random() < 0.5 else (y, x)))
    return clues


def minimal_clues(puzzle: LogicPuzzle, assignment: Assignment, rng: random.Random) -> list[LogicClue]:
    """Start from a set with one solution, then remove each clue whose removal keeps exactly one solution.

    The builder tries the "same" clues first, so the puzzle leans on the indirect clues.
    """
    direct: list[LogicClue] = same_clues(puzzle, assignment)
    others: list[LogicClue] = other_true_clues(puzzle, assignment, rng)
    indirect: list[LogicClue] = rng.sample(others, min(OTHER_CLUE_SAMPLE, len(others)))
    rng.shuffle(direct)
    kept: list[LogicClue] = direct + indirect
    for clue in list(kept):
        trial: list[LogicClue] = [other for other in kept if other is not clue]
        if has_one_solution(puzzle, trial):
            kept = trial
    rng.shuffle(kept)
    return kept


# Rendering


def templates_for(language: str) -> dict[str, str]:
    return CLUE_TEMPLATES.get(language, CLUE_TEMPLATES["en"])


def clue_sentence(clue: LogicClue, puzzle: LogicPuzzle, templates: dict[str, str]) -> str:
    texts: list[str] = [puzzle.items[category][item] for category, item in clue.refs]
    if clue.kind == "either":
        sentence: str = templates["either"].format(z=texts[0], x=texts[1], y=texts[2])
    else:
        sentence = templates[clue.kind].format(x=texts[0], y=texts[1])
    return sentence[0].upper() + sentence[1:]


def question_sentence(puzzle: LogicPuzzle, templates: dict[str, str]) -> str:
    return templates["question"].format(
        category=puzzle.names[puzzle.ask_category],
        item=puzzle.items[puzzle.question_category][puzzle.question_item],
    )


def order_sentence(puzzle: LogicPuzzle, templates: dict[str, str]) -> str | None:
    if puzzle.ordered is None:
        return None
    return templates["order"].format(
        category=puzzle.names[puzzle.ordered], items=", ".join(puzzle.items[puzzle.ordered])
    )


def clues_json(clues: list[LogicClue], puzzle: LogicPuzzle) -> str:
    return json.dumps(
        [
            {
                "kind": clue.kind,
                "refs": [[puzzle.names[category], puzzle.items[category][item]] for category, item in clue.refs],
            }
            for clue in clues
        ]
    )


def notes_table_html(puzzle: LogicPuzzle) -> str:
    header: str = "".join(f"<th>{escape(name)}</th>" for name in puzzle.names)
    rows: str = "".join(
        f"<tr><th>{escape(item)}</th>" + "<td></td>" * (len(puzzle.names) - 1) + "</tr>" for item in puzzle.items[0]
    )
    return f'<table class="mf-logic-notes"><tr>{header}</tr>{rows}</table>'


def logic_grid_html(puzzle: LogicPuzzle, sentences: list[str], question: str, order: str | None) -> str:
    order_html: str = "" if order is None else f'<p class="mf-logic-order">{escape(order)}</p>'
    clue_items: str = "".join(f"<li>{escape(sentence)}</li>" for sentence in sentences)
    return (
        f'{order_html}<ol class="mf-logic-clues">{clue_items}</ol>'
        f'<p class="mf-logic-question">{escape(question)}</p>{notes_table_html(puzzle)}'
    )


def build_logic_grid(params: LogicGridParams, context: MechanicContext) -> Artifact:
    puzzle: LogicPuzzle = logic_puzzle(params)
    rng: random.Random = random.Random(context.seed)
    assignment: Assignment = chosen_solution(params, puzzle, context, rng)
    clues: list[LogicClue] = minimal_clues(puzzle, assignment, rng)
    templates: dict[str, str] = templates_for(context.language)
    sentences: list[str] = [clue_sentence(clue, puzzle, templates) for clue in clues]
    question: str = question_sentence(puzzle, templates)
    order: str | None = order_sentence(puzzle, templates)
    category_lines: list[str] = [
        f"{name}: {', '.join(items)}" for name, items in zip(puzzle.names, puzzle.items, strict=True)
    ]
    solver_lines: list[str] = [
        *category_lines,
        *([] if order is None else [order]),
        "",
        "Clues:",
        *(f"{number}. {sentence}" for number, sentence in enumerate(sentences, start=1)),
        "",
        f"Question: {question}",
    ]
    return Artifact(
        html=f'<div class="mf-logic-grid" data-clues="{escape(clues_json(clues, puzzle))}">'
        f"{logic_grid_html(puzzle, sentences, question, order)}</div>",
        solver_text="\n".join(solver_lines),
    )


def decode_logic_grid(rendered: RenderedArtifact, params: LogicGridParams, context: MechanicContext) -> str:
    """Solve the structured clues of the page and answer the question. Return "" when they allow several solutions."""
    puzzle: LogicPuzzle = logic_puzzle(params)
    entries: list[dict[str, Any]] = json.loads(html.unescape(re.findall(r'data-clues="([^"]*)"', rendered.html)[0]))
    clues: list[LogicClue] = [
        LogicClue(
            entry["kind"],
            tuple(
                (puzzle.names.index(name), puzzle.items[puzzle.names.index(name)].index(item))
                for name, item in entry["refs"]
            ),
        )
        for entry in entries
    ]
    solutions: list[Assignment] = LogicSolver(puzzle, clues).solutions(limit=2)
    if len(solutions) != 1:
        return ""
    return asked_item(puzzle, solutions[0])


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(
        id="logic-grid", params_model=LogicGridParams, build=build_logic_grid, decode_rendered=decode_logic_grid
    ),
)
