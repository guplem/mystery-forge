"""Answer normalization and hashing.

Players type answers in many forms ("El Faro", "faro", "FARO!"). Every answer check (the companion page, the paper
answer register, the solver panel, the leak check) compares normalized answers, so this module is the single
definition of "the same answer". The JavaScript companion has a copy of the algorithm; `contracts/answer-vectors.json`
holds the shared test vectors that keep both copies equal.
"""

import hashlib
import re
import unicodedata

# Letters that Unicode decomposition (NFKD) does not split into a base letter plus a mark.
SPECIAL_LETTERS: dict[str, str] = {
    "æ": "ae",
    "œ": "oe",
    "ø": "o",
    "ł": "l",
    "đ": "d",
    "ð": "d",
    "þ": "th",
    "ı": "i",  # noqa: RUF001 (the dotless i is the point of this entry)
}

# A leading article is dropped only when another word follows it: "The" alone stays "the".
LEADING_ARTICLES: dict[str, frozenset[str]] = {
    "en": frozenset({"the", "a", "an"}),
    "es": frozenset({"el", "la", "los", "las", "un", "una", "unos", "unas"}),
    "ca": frozenset({"el", "la", "els", "les", "l", "un", "una"}),
    "fr": frozenset({"le", "la", "les", "l", "un", "une", "des"}),
    "de": frozenset({"der", "die", "das", "ein", "eine"}),
    "it": frozenset({"il", "lo", "la", "i", "gli", "le", "l", "un", "una", "uno"}),
    "pt": frozenset({"o", "a", "os", "as", "um", "uma"}),
}

WORD_PATTERN: re.Pattern[str] = re.compile(r"[a-z0-9]+")


def normalize_answer(text: str, language: str) -> str:
    """Return the comparable form of an answer: lowercase ASCII letters and digits, no accents, no leading article."""
    decomposed: str = unicodedata.normalize("NFKD", text)
    without_marks: str = "".join(character for character in decomposed if not unicodedata.combining(character))
    folded: str = without_marks.casefold()
    transliterated: str = "".join(SPECIAL_LETTERS.get(character, character) for character in folded)
    words: list[str] = WORD_PATTERN.findall(transliterated)
    articles: frozenset[str] = LEADING_ARTICLES.get(language, frozenset())
    if len(words) > 1 and words[0] in articles:
        words = words[1:]
    return "".join(words)


def answer_hash(normalized_answer: str, salt: str) -> str:
    """Return the SHA-256 hex digest of `<salt>:<normalized answer>`, the form that the companion page stores."""
    return hashlib.sha256(f"{salt}:{normalized_answer}".encode()).hexdigest()
