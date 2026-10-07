"""Answer normalization and hashing.

Players type answers in many forms ("El Faro", "faro", "FARO!"). Every answer check (the companion page, the paper
answer register, the solver panel, the leak check) compares normalized answers, so this module is the single
definition of "the same answer". The JavaScript companion has a copy of the algorithm; `contracts/answer-vectors.json`
holds the shared test vectors that keep both copies equal.
"""

import hashlib
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

# The first letter that keeps its marks: Armenian. Below it lie Latin, Greek, and Cyrillic.
FIRST_MARKED_SCRIPT: int = 0x0530
# Latin Extended Additional and Greek Extended: their letters lose their accents too.
EXTENDED_ACCENTED: range = range(0x1E00, 0x2000)
# Letters, digits, and marks of every script. A mark of a script outside Latin, Greek, and Cyrillic is part of its
# letter (a Devanagari vowel sign), so it stays.
WORD_CATEGORIES: frozenset[str] = frozenset({"L", "N", "M"})


def drops_accent(base: str) -> bool:
    """True when a mark on this base letter is only an accent: in Latin, Greek, and Cyrillic, "é" counts as "e"."""
    code: int = ord(base)
    return code < FIRST_MARKED_SCRIPT or code in EXTENDED_ACCENTED


def without_accents(decomposed: str) -> str:
    kept: list[str] = []
    base: str = ""
    for character in decomposed:
        # The Unicode category M, the same test as \p{M} in the JavaScript copy.
        if not unicodedata.category(character).startswith("M"):
            base = character
        elif base and drops_accent(base):
            continue
        kept.append(character)
    # Compose again, so a kana with its voicing mark or a Hangul syllable is one character, as players type it.
    return unicodedata.normalize("NFC", "".join(kept))


def answer_words(text: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for character in text:
        if unicodedata.category(character)[0] in WORD_CATEGORIES:
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def normalize_answer(text: str, language: str) -> str:
    """Return the comparable form of an answer: lowercase letters and digits of any script, no Latin, Greek, or
    Cyrillic accents, no punctuation or spaces, and no leading article."""
    folded: str = without_accents(unicodedata.normalize("NFKD", text)).casefold()
    transliterated: str = "".join(SPECIAL_LETTERS.get(character, character) for character in folded)
    words: list[str] = answer_words(transliterated)
    articles: frozenset[str] = LEADING_ARTICLES.get(language, frozenset())
    if len(words) > 1 and words[0] in articles:
        words = words[1:]
    return "".join(words)


def answer_hash(normalized_answer: str, salt: str) -> str:
    """Return the SHA-256 hex digest of `<salt>:<normalized answer>`, the form that the companion page stores."""
    return hashlib.sha256(f"{salt}:{normalized_answer}".encode()).hexdigest()
