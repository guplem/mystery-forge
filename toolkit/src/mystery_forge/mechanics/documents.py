"""Mechanics built on documents: book cipher, cut strips, and timeline order."""

import html
import math
import random
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from markupsafe import escape
from pydantic import BaseModel, Field

from mystery_forge import i18n
from mystery_forge.answers import normalize_answer
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)

NO_ANSWER_LETTERS_ERROR: tuple[str, str] = (
    "The answer has no letters or digits.",
    "Give the puzzle an answer with at least one letter or digit.",
)


def fold(text: str) -> str:
    """Return the letters and digits of a text, lowercase and without accents."""
    return normalize_answer(text, "")


def require_answer_letters(context: MechanicContext) -> str:
    if not context.normalized_answer:
        raise MechanicBuildError(*NO_ANSWER_LETTERS_ERROR)
    return context.normalized_answer


def shuffled_order(count: int, rng: random.Random) -> list[int]:
    """Return a shuffled order of `count` positions that is never the sorted order, so the puzzle is never solved."""
    order: list[int] = list(range(count))
    rng.shuffle(order)
    if order == sorted(order):
        order = order[1:] + order[:1]
    return order


# book-cipher


class BookCipherParams(BaseModel):
    document: str = Field(description="The id of the document that the references point into.")
    unit: Literal["word", "letter"] = Field(
        default="letter",
        description='"letter": each reference points to a word whose first letter is the next answer letter. '
        '"word": each reference points to the next word of the answer.',
    )
    reference_style: Literal["line.word", "word"] = Field(
        default="line.word",
        description='"line.word": "3.4" is word 4 of line 3 (empty lines do not count). "word": "17" is word 17.',
    )


@dataclass(frozen=True)
class DocumentWord:
    line_number: int
    word_in_line: int
    word_number: int
    folded: str


def document_words(text: str) -> list[DocumentWord]:
    """Split a document into the words that a player counts: tokens with at least one letter or digit."""
    words: list[DocumentWord] = []
    line_number: int = 0
    for line in text.splitlines():
        folded_tokens: list[str] = [fold(token) for token in line.split() if fold(token)]
        if folded_tokens:
            line_number += 1
        for word_in_line, folded in enumerate(folded_tokens, start=1):
            words.append(DocumentWord(line_number, word_in_line, len(words) + 1, folded))
    return words


def reference_of(word: DocumentWord, reference_style: str) -> str:
    if reference_style == "word":
        return str(word.word_number)
    return f"{word.line_number}.{word.word_in_line}"


def cipher_targets(params: BookCipherParams, context: MechanicContext) -> list[str]:
    if params.unit == "letter":
        return list(require_answer_letters(context))
    targets: list[str] = [fold(word) for word in context.answer.split() if fold(word)]
    if not targets:
        raise MechanicBuildError(*NO_ANSWER_LETTERS_ERROR)
    return targets


def matches_target(word: DocumentWord, target: str, unit: str) -> bool:
    return word.folded == target if unit == "word" else word.folded[0] == target


def missing_target_error(params: BookCipherParams, target: str) -> MechanicBuildError:
    if params.unit == "word":
        return MechanicBuildError(
            f"The document '{params.document}' does not contain the word '{target}'.",
            fix_hint=f"Add the word '{target}' to the document, or use the unit 'letter'.",
        )
    return MechanicBuildError(
        f"No word in the document '{params.document}' starts with '{target}'.",
        fix_hint=f"Add a word that starts with '{target}' to the document, or use another document.",
    )


def build_book_cipher(params: BookCipherParams, context: MechanicContext) -> Artifact:
    if params.document not in context.documents:
        raise MechanicBuildError(
            f"The document '{params.document}' does not exist.",
            fix_hint=f"Use one of these document ids: {', '.join(sorted(context.documents))}.",
        )
    words: list[DocumentWord] = document_words(context.documents[params.document])
    rng: random.Random = random.Random(context.seed)
    used: set[int] = set()
    references: list[str] = []
    for target in cipher_targets(params, context):
        candidates: list[DocumentWord] = [word for word in words if matches_target(word, target, params.unit)]
        if not candidates:
            raise missing_target_error(params, target)
        unused: list[DocumentWord] = [word for word in candidates if word.word_number not in used]
        chosen: DocumentWord = rng.choice(unused or candidates)
        used.add(chosen.word_number)
        references.append(reference_of(chosen, params.reference_style))
    reference_line: str = " ".join(references)
    return Artifact(html=f'<p class="mf-book-cipher">{escape(reference_line)}</p>', solver_text=reference_line)


def decode_book_cipher(rendered: RenderedArtifact, params: BookCipherParams, context: MechanicContext) -> str:
    """Read the references back and look them up in the document text.

    The round-trip check must place the rendered text of the document in `context.documents`, so that the check also
    covers a document whose rendering changed a word.
    """
    if params.document not in context.documents:
        raise MechanicBuildError(
            f"The document '{params.document}' is not in the context.",
            fix_hint="Place the rendered text of the document in the context before the round-trip check.",
        )
    words_by_reference: dict[str, DocumentWord] = {
        reference_of(word, params.reference_style): word for word in document_words(context.documents[params.document])
    }
    found: list[str] = [
        words_by_reference[reference].folded
        for reference in re.findall(r"\d+(?:\.\d+)?", rendered.text)
        if reference in words_by_reference
    ]
    if params.unit == "word":
        return " ".join(found)
    return "".join(word[0] for word in found)


# cut-strips

STRIP_SYMBOLS: tuple[str, ...] = ("★", "◆", "▲", "■", "♣", "♠", "♥", "♦", "☀", "☾", "✚", "✿")
STRIP_DOT: str = "•"
NO_BREAK_SPACE: str = "\u00a0"


class CutStripsParams(BaseModel):
    message: str = Field(description="The sentence that the strips show once they are in order. It holds the answer.")
    strips: int = Field(default=6, ge=2, le=len(STRIP_SYMBOLS), description="The number of strips.")
    orientation: Literal["vertical", "horizontal"] = Field(
        default="vertical",
        description='"vertical": each strip holds a few columns of every text row. "horizontal": one text line each.',
    )
    rows: int = Field(default=4, ge=1, le=10, description="Vertical strips only: the target number of text rows.")


def horizontal_strip_lines(message: str, strip_count: int) -> list[list[str]]:
    base_length, longer_count = divmod(len(message), strip_count)
    lines: list[list[str]] = []
    start: int = 0
    for position in range(strip_count):
        length: int = base_length + (1 if position < longer_count else 0)
        lines.append([message[start : start + length]])
        start += length
    return lines


def vertical_strip_lines(message: str, strip_count: int, target_rows: int) -> list[list[str]]:
    columns_per_strip: int = math.ceil(len(message) / (strip_count * target_rows))
    row_width: int = strip_count * columns_per_strip
    row_count: int = math.ceil(len(message) / row_width)
    padded: str = message.ljust(row_count * row_width)
    return [
        [
            padded[
                row * row_width + position * columns_per_strip : row * row_width + (position + 1) * columns_per_strip
            ]
            for row in range(row_count)
        ]
        for position in range(strip_count)
    ]


def strip_html(symbol: str, dot_count: int, lines: list[str]) -> str:
    line_spans: str = "".join(
        f'<span class="mf-strip-line">{escape(line.replace(" ", NO_BREAK_SPACE))}</span>' for line in lines
    )
    return (
        f'<div class="mf-strip" data-symbol="{escape(symbol)}"><span class="mf-strip-symbol">{escape(symbol)}</span>'
        f'<span class="mf-strip-dots">{STRIP_DOT * dot_count}</span>{line_spans}</div>'
    )


def build_cut_strips(params: CutStripsParams, context: MechanicContext) -> Artifact:
    answer: str = require_answer_letters(context)
    message: str = " ".join(params.message.split())
    if answer not in fold(message):
        raise MechanicBuildError(
            f"The message does not contain the answer '{answer}'.", fix_hint="Write the answer inside the message."
        )
    if len(message) < params.strips:
        raise MechanicBuildError(
            f"The message has {len(message)} characters, fewer than the {params.strips} strips.",
            fix_hint="Write a longer message or use fewer strips.",
        )
    lines_by_position: list[list[str]] = (
        horizontal_strip_lines(message, params.strips)
        if params.orientation == "horizontal"
        else vertical_strip_lines(message, params.strips, params.rows)
    )
    order: list[int] = shuffled_order(params.strips, random.Random(context.seed))
    strip_parts: list[str] = []
    solver_lines: list[str] = []
    for symbol, position in zip(STRIP_SYMBOLS, order, strict=False):
        strip_parts.append(strip_html(symbol, position + 1, lines_by_position[position]))
        solver_lines.append(f"Strip {symbol}, {position + 1} dots: " + " / ".join(lines_by_position[position]))
    return Artifact(
        html=f'<div class="mf-cut-strips mf-cut-strips-{params.orientation}">{"".join(strip_parts)}</div>',
        solver_text="\n".join(solver_lines),
        print_notes=(i18n.text(context.language, "print_cut_strips"),),
    )


def decode_cut_strips(rendered: RenderedArtifact, params: CutStripsParams, context: MechanicContext) -> str:
    """Put the strips in dot order and read the message. Return the answer when the message contains it."""
    strips: list[tuple[int, list[str]]] = []
    for block in re.findall(r'<div class="mf-strip"[^>]*>(.*?)</div>', rendered.html, flags=re.DOTALL):
        dots: str = re.findall(r'<span class="mf-strip-dots">(.*?)</span>', block)[0]
        lines: list[str] = [
            html.unescape(line) for line in re.findall(r'<span class="mf-strip-line">(.*?)</span>', block)
        ]
        strips.append((dots.count(STRIP_DOT), lines))
    strips.sort(key=lambda strip: strip[0])
    row_count: int = len(strips[0][1])
    message: str = "".join("".join(lines[row] for _dots, lines in strips) for row in range(row_count))
    if context.normalized_answer in fold(message):
        return context.answer
    return message


# timeline-order

TIMELINE_FORMAT: str = "%Y-%m-%d %H:%M"


class TimelineEvent(BaseModel):
    when: str = Field(description='The date and time of the event, as "YYYY-MM-DD HH:MM".')
    text: str = Field(description="What happened. Its first letter is the next answer letter in date order.")


class TimelineOrderParams(BaseModel):
    events: list[TimelineEvent] = Field(
        min_length=2, max_length=20, description="The events. In date order, their first letters spell the answer."
    )


def parse_event_time(event: TimelineEvent) -> datetime:
    try:
        return datetime.strptime(event.when.strip(), TIMELINE_FORMAT)
    except ValueError as error:
        raise MechanicBuildError(
            f"The event '{event.text}' has the date '{event.when}', which is not in the form YYYY-MM-DD HH:MM.",
            fix_hint="Write the date as YYYY-MM-DD HH:MM, for example 1923-05-02 21:15.",
        ) from error


def sorted_events(events: list[TimelineEvent]) -> list[tuple[str, TimelineEvent]]:
    """Return the events with their canonical date text, in date order. Reject repeated dates and empty texts."""
    dated: dict[str, TimelineEvent] = {}
    for event in events:
        when: str = parse_event_time(event).strftime(TIMELINE_FORMAT)
        if when in dated:
            raise MechanicBuildError(
                f"Two events happen at {when}.", fix_hint="Give every event a different date and time."
            )
        if not fold(event.text):
            raise MechanicBuildError(
                f"The event at {when} has no letters.", fix_hint="Start the event text with the next answer letter."
            )
        dated[when] = event
    return sorted(dated.items())


def timeline_card_html(when: str, text: str) -> str:
    return (
        f'<div class="mf-timeline-card" data-when="{escape(when)}"><p class="mf-timeline-when">{escape(when)}</p>'
        f'<p class="mf-timeline-text">{escape(text)}</p></div>'
    )


def build_timeline_order(params: TimelineOrderParams, context: MechanicContext) -> Artifact:
    answer: str = require_answer_letters(context)
    ordered: list[tuple[str, TimelineEvent]] = sorted_events(params.events)
    spelled: str = "".join(fold(event.text)[0] for _when, event in ordered)
    if spelled != answer:
        raise MechanicBuildError(
            f"In date order, the first letters spell '{spelled}', not the answer '{answer}'.",
            fix_hint="Change the event texts or dates so that the first letters spell the answer.",
        )
    shown: list[tuple[str, TimelineEvent]] = [
        ordered[position] for position in shuffled_order(len(ordered), random.Random(context.seed))
    ]
    cards: str = "".join(timeline_card_html(when, event.text) for when, event in shown)
    return Artifact(
        html=f'<div class="mf-timeline">{cards}</div>',
        solver_text="\n".join(f"{when} | {event.text}" for when, event in shown),
    )


def decode_timeline_order(rendered: RenderedArtifact, params: TimelineOrderParams, context: MechanicContext) -> str:
    cards: list[tuple[str, str]] = re.findall(
        r'data-when="([^"]+)">.*?<p class="mf-timeline-text">(.*?)</p>', rendered.html, flags=re.DOTALL
    )
    return "".join(fold(html.unescape(text))[0] for _when, text in sorted(cards))


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(
        id="book-cipher", params_model=BookCipherParams, build=build_book_cipher, decode_rendered=decode_book_cipher
    ),
    MechanicImplementation(
        id="cut-strips", params_model=CutStripsParams, build=build_cut_strips, decode_rendered=decode_cut_strips
    ),
    MechanicImplementation(
        id="timeline-order",
        params_model=TimelineOrderParams,
        build=build_timeline_order,
        decode_rendered=decode_timeline_order,
    ),
)
