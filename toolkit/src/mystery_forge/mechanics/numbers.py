"""Number mechanics: the answer is a code made of digits.

`arithmetic-lock` verifies the arithmetic that leads to the code (the clues live in documents) and draws a lock.
`clock-faces` draws one clock per digit of the code.
"""

import ast
import math
import operator
import random
from collections.abc import Callable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)
from mystery_forge.mechanics.text_tools import attribute_values

STROKE_ATTRIBUTES: str = 'fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"'


def digits_answer(context: MechanicContext) -> str:
    """Return the normalized answer, which must be digits only."""
    if not context.normalized_answer.isdigit():
        raise MechanicBuildError(
            f"The answer '{context.answer}' is not a number made of digits only.",
            fix_hint="Give the puzzle a code made of digits only, such as 0427.",
        )
    return context.normalized_answer


# arithmetic-lock

OPERATORS: dict[type[ast.operator], Callable[[int, int], int]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
}
SAFE_SET_HINT: str = "Use only the step labels, whole numbers, + - * // and parentheses."


class ArithmeticStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="The name of the number in the expression, such as 'boxes'. Letters, digits, _.")
    value: int = Field(description="The whole number that the players find for this step in the documents.")


class ArithmeticLockParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[ArithmeticStep] = Field(
        description="The numbers that the players find in the documents, each with a label for the expression."
    )
    expression: str = Field(
        description="How the step numbers give the code, such as '(boxes * keys - 4) // 2'. "
        "Use only the labels, whole numbers, + - * // and parentheses."
    )
    digits: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="The number of dials on the lock. Leave it empty to use the length of the answer.",
    )


def step_values(steps: list[ArithmeticStep]) -> dict[str, int]:
    values: dict[str, int] = {}
    for step in steps:
        if not step.label.isidentifier():
            raise MechanicBuildError(
                f"The step label '{step.label}' is not a valid name.",
                fix_hint="Use letters, digits, and underscores, starting with a letter, such as 'boxes' or 'room_2'.",
            )
        if step.label in values:
            raise MechanicBuildError(
                f"The step label '{step.label}' appears more than once.",
                fix_hint="Give each step its own label.",
            )
        values[step.label] = step.value
    return values


def evaluate(node: ast.expr, values: Mapping[str, int], expression: str) -> int:
    """Evaluate the safe subset of Python arithmetic; refuse every other node."""
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left: int = evaluate(node.left, values, expression)
        right: int = evaluate(node.right, values, expression)
        if isinstance(node.op, ast.FloorDiv) and right == 0:
            raise MechanicBuildError(f"The expression '{expression}' divides by zero.", fix_hint=SAFE_SET_HINT)
        return OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -evaluate(node.operand, values, expression)
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return int(node.value)
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise MechanicBuildError(
                f"The expression '{expression}' uses '{node.id}', which is not a step label.",
                fix_hint=f"Use only these labels: {', '.join(values)}.",
            )
        return values[node.id]
    raise MechanicBuildError(
        f"The expression '{expression}' uses '{ast.unparse(node)}', which the lock does not allow.",
        fix_hint=SAFE_SET_HINT,
    )


def parsed_expression(expression: str) -> ast.expr:
    try:
        return ast.parse(expression, mode="eval").body
    except SyntaxError as error:
        raise MechanicBuildError(
            f"The expression '{expression}' is not valid arithmetic.", fix_hint=SAFE_SET_HINT
        ) from error


def lock_svg(dial_count: int) -> str:
    width: int = 20 + 30 * dial_count
    middle: float = width / 2
    dials: str = "".join(
        f'<rect class="mf-lock-dial" x="{15 + 30 * index}" y="52" width="20" height="24" rx="3" stroke-width="2"/>'
        for index in range(dial_count)
    )
    return (
        f'<svg class="mf-lock" data-dials="{dial_count}" viewBox="0 0 {width} 90"><g {STROKE_ATTRIBUTES} '
        f'stroke-width="3"><path d="M{middle - 18:g} 40 V24 A18 18 0 0 1 {middle + 18:g} 24 V40"/>'
        f'<rect x="5" y="40" width="{width - 10}" height="46" rx="6"/>{dials}</g></svg>'
    )


def build_arithmetic_lock(params: ArithmeticLockParams, context: MechanicContext) -> Artifact:
    answer: str = digits_answer(context)
    values: dict[str, int] = step_values(params.steps)
    dial_count: int = len(answer) if params.digits is None else params.digits
    if dial_count != len(answer):
        raise MechanicBuildError(
            f"The lock has {dial_count} dials, but the answer '{context.answer}' has {len(answer)} digits.",
            fix_hint="Leave digits empty, or set it to the number of digits in the answer.",
        )
    result: int = evaluate(parsed_expression(params.expression), values, params.expression)
    # A negative result never matches: the zero padding of -5 gives '-05', and an answer has no minus sign.
    if f"{result:0{dial_count}d}" != answer:
        raise MechanicBuildError(
            f"The expression '{params.expression}' gives {result}, but the answer is '{context.answer}'.",
            fix_hint="Change the step values or the expression so that the result is the answer.",
        )
    return Artifact(
        html=f'<div class="mf-arithmetic-lock">{lock_svg(dial_count)}</div>',
        solver_text=f"A combination lock with {dial_count} digit dials.",
    )


# clock-faces

CLOCK_CENTER: int = 50
HOUR_HAND_LENGTH: int = 24
MINUTE_HAND_LENGTH: int = 36


class ClockFacesParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["hour", "minute"] = Field(
        default="hour",
        description="'hour': the hour hand points at the digit (12 stands for 0) and the minute hand at 12. "
        "'minute': the minute hand points at the digit (minutes = digit x 5) and the hour hand is a decoy.",
    )


def point_on_clock(angle_degrees: float, length: int) -> tuple[str, str]:
    """Return the end of a hand as SVG coordinates; 0 degrees points at 12, and angles grow clockwise."""
    angle: float = math.radians(angle_degrees)
    x: float = CLOCK_CENTER + length * math.sin(angle)
    y: float = CLOCK_CENTER - length * math.cos(angle)
    return f"{round(x, 2):g}", f"{round(y, 2):g}"


def clock_ticks() -> str:
    ticks: list[str] = []
    for hour in range(12):
        # The 12 o'clock tick is longer, so the players can see which way is up.
        outer_x, outer_y = point_on_clock(hour * 30, 44)
        inner_x, inner_y = point_on_clock(hour * 30, 34 if hour == 0 else 39)
        ticks.append(f'<line x1="{inner_x}" y1="{inner_y}" x2="{outer_x}" y2="{outer_y}" stroke-width="2"/>')
    return "".join(ticks)


def clock_svg(digit: str, hour: int, minute: int) -> str:
    hour_x, hour_y = point_on_clock((hour % 12) * 30 + minute * 0.5, HOUR_HAND_LENGTH)
    minute_x, minute_y = point_on_clock(minute * 6, MINUTE_HAND_LENGTH)
    return (
        f'<svg class="mf-glyph mf-clock" data-symbol="{digit}" viewBox="0 0 100 100"><g {STROKE_ATTRIBUTES}>'
        f'<circle cx="50" cy="50" r="46" stroke-width="3"/>{clock_ticks()}'
        f'<line class="mf-clock-hour" x1="50" y1="50" x2="{hour_x}" y2="{hour_y}" stroke-width="6"/>'
        f'<line class="mf-clock-minute" x1="50" y1="50" x2="{minute_x}" y2="{minute_y}" stroke-width="3"/>'
        f'<circle cx="50" cy="50" r="3" fill="currentColor" stroke="none"/></g></svg>'
    )


def clock_time(digit: int, mode: str, rng: random.Random) -> tuple[int, int]:
    if mode == "hour":
        return (digit if digit > 0 else 12), 0
    return rng.randint(1, 12), digit * 5


def build_clock_faces(params: ClockFacesParams, context: MechanicContext) -> Artifact:
    rng: random.Random = random.Random(context.seed)
    times: list[tuple[int, int]] = [clock_time(int(digit), params.mode, rng) for digit in digits_answer(context)]
    clocks: str = "".join(
        clock_svg(digit, hour, minute) for digit, (hour, minute) in zip(context.normalized_answer, times, strict=True)
    )
    return Artifact(
        html=f'<div class="mf-clock-faces">{clocks}</div>',
        solver_text=" ".join(
            f"Clock {number} shows {hour}:{minute:02d}." for number, (hour, minute) in enumerate(times, start=1)
        ),
    )


def decode_clock_faces(rendered: RenderedArtifact, params: ClockFacesParams, context: MechanicContext) -> str:
    return "".join(attribute_values(rendered.html, "data-symbol"))


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(id="arithmetic-lock", params_model=ArithmeticLockParams, build=build_arithmetic_lock),
    MechanicImplementation(
        id="clock-faces", params_model=ClockFacesParams, build=build_clock_faces, decode_rendered=decode_clock_faces
    ),
)
