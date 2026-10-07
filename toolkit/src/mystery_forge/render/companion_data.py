"""The companion page: one offline HTML file that checks answers, gives hints, and scores the accusation.

The page must work from `file://` in every browser, so this module inlines every script, the style sheet, and the
game data into one HTML string. The data never holds an answer in plain text, except inside the solutions, which the
page shows only after a confirm: answers, near misses, and the correct accusation options are salted hashes
(`mystery_forge.answers.answer_hash`), and the page hashes what players type in the same way.
"""

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any, Final

from jinja2 import Environment, StrictUndefined

from mystery_forge.answers import answer_hash, normalize_answer
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.i18n import STRINGS, known_language, text
from mystery_forge.spec.models import AccusationQuestion, Deduction

COMPANION_FOLDER: Final[str] = "companion"
TEMPLATE_FILE: Final[str] = "companion.html.j2"
# In the order that the page loads them: the logic files must exist before the app file runs.
STYLE_FILE: Final[str] = "companion.css"
SCRIPT_FILES: Final[tuple[str, ...]] = ("answers.js", "companionLogic.js", "companionApp.js")
COMPANION_STATIC_FILES: Final[tuple[str, ...]] = (STYLE_FILE, *SCRIPT_FILES)
COMPANION_TEXT_PREFIX: Final[str] = "companion_"
DATA_FORMAT_VERSION: Final[int] = 1


def build_companion_data(game: Game) -> dict[str, Any]:
    """Return the JSON-serializable data that the companion page reads."""
    codes: dict[str, str] = {puzzle.source.id: puzzle.code for puzzle in game.puzzles}
    unlocks: dict[str, str] = {stage.opens_with: stage.id for stage in game.flow.stages if stage.opens_with != "start"}
    puzzles: list[AssembledPuzzle] = sorted(
        game.puzzles, key=lambda puzzle: (puzzle.source.stage, int(puzzle.code[1:]))
    )
    final_puzzle: str | None = game.flow.final_puzzle
    return {
        "format_version": DATA_FORMAT_VERSION,
        "title": game.story.title,
        "tagline": game.story.tagline,
        "intro": game.story.intro,
        "language": game.config.language,
        "salt": game.salt,
        "duration_minutes": game.config.duration_minutes,
        # The solver panel does not exist yet; the page reads this flag once it does.
        "panel_verified": True,
        "final_puzzle": codes[final_puzzle] if final_puzzle is not None else None,
        "ui": companion_texts(game.config.language),
        "stages": [
            {
                "id": stage.id,
                "label": stage.label,
                "envelope": text(game.config.language, "envelope_label", stage=stage.id),
                "opens_with": "start" if stage.opens_with == "start" else codes[stage.opens_with],
                "opening_text": stage.opening_text,
            }
            for stage in game.flow.stages
        ],
        "puzzles": [puzzle_data(puzzle, unlocks.get(puzzle.source.id), game) for puzzle in puzzles],
        "deduction": deduction_data(game.story.deduction, game.salt),
        "epilogues": [
            {"min_score_percent": epilogue.min_score_percent, "title": epilogue.title, "text": epilogue.text}
            for epilogue in sorted(game.story.epilogues, key=lambda epilogue: -epilogue.min_score_percent)
        ],
        "reveal": [step.text for step in game.story.reveal],
    }


def companion_texts(language: str) -> dict[str, str]:
    strings: dict[str, str] = STRINGS[known_language(language)]
    return {
        key.removeprefix(COMPANION_TEXT_PREFIX): value
        for key, value in strings.items()
        if key.startswith(COMPANION_TEXT_PREFIX)
    }


def puzzle_data(puzzle: AssembledPuzzle, unlocks: str | None, game: Game) -> dict[str, Any]:
    language: str = game.config.language
    source = puzzle.source
    return {
        "code": puzzle.code,
        "title": source.title,
        "stage": source.stage,
        "answer_format": source.answer_format.label,
        "answer_hashes": [answer_hash(answer, game.salt) for answer in puzzle.accepted_normalized],
        "near_misses": [
            {"hash": answer_hash(normalize_answer(near_miss.answer, language), game.salt), "message": near_miss.message}
            for near_miss in source.near_misses
        ],
        "unlocks": unlocks,
        "hints": [{"level": hint.level, "text": hint.text} for hint in source.hints],
        "solution": {"steps": [step.text for step in source.solution], "answer": source.answer},
        "reveal_text": source.reveal_text,
    }


def deduction_data(deduction: Deduction | None, salt: str) -> dict[str, Any] | None:
    if deduction is None:
        return None
    return {"questions": [question_data(question, salt) for question in deduction.questions]}


def question_data(question: AccusationQuestion, salt: str) -> dict[str, Any]:
    return {
        "id": question.id,
        "prompt": question.prompt,
        "options": [{"id": option.id, "text": option.text} for option in question.options],
        # The question id is part of the hashed text, so two questions that share option ids get different hashes.
        "correct_hash": answer_hash(f"{question.id}:{question.correct}", salt),
        "points": question.points,
    }


def script_safe_json(value: Any) -> str:
    """Return JSON that cannot end its `<script>` element early, whatever text the story holds."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "\\u003c!--")


def build_companion_html(game: Game) -> str:
    """Return the whole companion page as one self-contained HTML string."""
    folder: Traversable = files("mystery_forge.render").joinpath(COMPANION_FOLDER)
    environment = Environment(autoescape=True, undefined=StrictUndefined, keep_trailing_newline=True)
    template = environment.from_string(folder.joinpath(TEMPLATE_FILE).read_text(encoding="utf-8"))
    return template.render(
        language=game.config.language,
        title=game.story.title,
        style=folder.joinpath(STYLE_FILE).read_text(encoding="utf-8"),
        scripts=[folder.joinpath(name).read_text(encoding="utf-8") for name in SCRIPT_FILES],
        data_json=script_safe_json(build_companion_data(game)),
    )
