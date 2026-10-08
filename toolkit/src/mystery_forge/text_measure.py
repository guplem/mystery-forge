"""Text measures that work in every script: a word count for the reading budget, and a width for the page layout.

Japanese, Chinese, and Thai write no spaces between words, so a count of the spaces sees a whole paragraph as one
word. For those scripts, every two letters count as one word, which is close to the reading time of a word.
"""

import math
import unicodedata
from typing import Final

# About two characters of these scripts carry the meaning of one word.
CHARACTERS_PER_WORD: Final[int] = 2
# The scripts that write no spaces between words: CJK ideographs, Japanese kana, Thai, Lao, Khmer, and Myanmar.
NO_SPACE_RANGES: Final[tuple[range, ...]] = (
    range(0x0E00, 0x0F00),  # Thai and Lao
    range(0x1000, 0x10A0),  # Myanmar
    range(0x1780, 0x1800),  # Khmer
    range(0x3040, 0x3100),  # Hiragana and Katakana
    range(0x31F0, 0x3200),  # Katakana phonetic extensions
    range(0x3400, 0x4DC0),  # CJK extension A
    range(0x4E00, 0xA000),  # CJK unified ideographs
    range(0xF900, 0xFB00),  # CJK compatibility ideographs
    range(0xFF66, 0xFFA0),  # Half-width katakana
    range(0x20000, 0x30000),  # CJK extensions B and later
)
WIDE_WIDTHS: Final[frozenset[str]] = frozenset({"W", "F"})


def writes_without_spaces(character: str) -> bool:
    code: int = ord(character)
    return any(code in block for block in NO_SPACE_RANGES)


def count_words(text: str) -> int:
    """Count the words of a text: each spaced word once, and every two letters of a script without spaces once."""
    total: int = 0
    for token in text.split():
        letters: list[str] = [character for character in token if unicodedata.category(character)[0] in "LN"]
        unspaced: int = sum(1 for character in letters if writes_without_spaces(character))
        total += math.ceil(unspaced / CHARACTERS_PER_WORD) + (1 if len(letters) > unspaced else 0)
    return total


def display_length(text: str) -> int:
    """The width of a text in Latin-letter widths: a full-width character, such as a kanji, takes two."""
    return sum(2 if unicodedata.east_asian_width(character) in WIDE_WIDTHS else 1 for character in text)
