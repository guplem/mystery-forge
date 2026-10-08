"""Height estimates for the pages that the toolkit fills from a list, and the split of a text that is too long.

The toolkit builds some pages from lists of any length: the answer register, the result paragraphs, the notes grid,
the hint cards, the solutions, the accusation form, and the manual. The planners use these estimates for a first
layout. With a browser, the renderer then measures each page; when a page of a flow group still overflows, it raises
the group's tightness level, so that group gets a smaller budget per page, and renders again.
"""

import math
import re
from collections.abc import Mapping
from typing import Final

from mystery_forge.config import Paper
from mystery_forge.text_measure import display_length

# The height of the safe area of one sheet: the paper height minus the 12 mm margin at the top and at the bottom.
SAFE_HEIGHT_MM: Final[dict[Paper, float]] = {"A4": 297 - 24, "Letter": 279.4 - 24}
# Each tightness level gives a flow group this share of the budget of the level before.
TIGHTEN_FACTOR: Final[float] = 0.8
SENTENCE_END: Final[re.Pattern[str]] = re.compile(r"(?<=[.!?…])\s+")

# The flow groups: each one is a list that the toolkit spreads over as many sheets as it needs.
Tightness = Mapping[str, int]


def tightness(levels: Tightness, group: str) -> int:
    return levels.get(group, 0)


def page_budget(paper: Paper, reserved_mm: float, level: int) -> float:
    """The height in millimetres that a flow group may fill on one sheet, after the parts that every sheet has."""
    return (SAFE_HEIGHT_MM[paper] - reserved_mm) * TIGHTEN_FACTOR**level


def text_height(text: str, chars_per_line: int, line_mm: float) -> float:
    """Estimate the height of a text: its wrapped lines, with each line break starting a new line."""
    lines: int = sum(max(1, math.ceil(display_length(line) / chars_per_line)) for line in text.split("\n"))
    return lines * line_mm


def split_words(sentence: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    current: str = ""
    for word in sentence.split():
        while len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:max_chars])
            word = word[max_chars:]
        candidate: str = f"{current} {word}" if current else word
        if len(candidate) > max_chars:
            pieces.append(current)
            candidate = word
        current = candidate
    # The caller passes a sentence longer than `max_chars`, so the last piece is never empty.
    pieces.append(current)
    return pieces


def split_text(text: str, max_chars: int) -> list[str]:
    """Split a text into pieces of at most `max_chars`: at sentence ends when it can, else between words."""
    pieces: list[str] = []
    current: str = ""
    for sentence in SENTENCE_END.split(text.strip()):
        for part in split_words(sentence, max_chars) if len(sentence) > max_chars else [sentence]:
            candidate: str = f"{current} {part}" if current else part
            if len(candidate) > max_chars:
                pieces.append(current)
                candidate = part
            current = candidate
    if current:
        pieces.append(current)
    return pieces
