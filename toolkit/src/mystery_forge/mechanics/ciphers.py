"""Cipher mechanics: the builder encodes a message that contains the answer, and the decoder reads it back.

Every cipher takes an optional `plaintext`, so the agent can encode a whole message (such as "MEET AT THE OLD MILL")
that contains the answer. The decoder returns the whole decoded message; the round-trip check tests that it contains
the answer.
"""

import random
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    RenderedArtifact,
)
from mystery_forge.mechanics.text_tools import (
    LETTERS,
    cyclic_permutation,
    escape_text,
    fold_text,
    marked_texts,
    plaintext_for,
    require_no_digits,
)

PLAINTEXT_DESCRIPTION: str = (
    "The message to encode. It must contain the answer. Leave it empty to encode the answer alone. "
    "Accents are removed and letters become uppercase."
)
ALPHABET: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cipher_html(mechanic_id: str, ciphertext: str, extra_html: str = "") -> str:
    return (
        f'<div class="mf-cipher mf-{mechanic_id}"><p class="mf-ciphertext">{escape_text(ciphertext)}</p>'
        f"{extra_html}</div>"
    )


def rendered_ciphertext(rendered: RenderedArtifact) -> str:
    return " ".join(marked_texts(rendered.html, "mf-ciphertext"))


def shift_letters(text: str, shift: int) -> str:
    return "".join(
        ALPHABET[(ALPHABET.index(character) + shift) % 26] if character in LETTERS else character for character in text
    )


class CaesarParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION)
    shift: int = Field(default=3, ge=1, le=25, description="How many places each letter moves forward (1 to 25).")
    show_shift: bool = Field(
        default=False, description="Print a key such as 'A = D' next to the ciphertext, for an easy puzzle."
    )


def build_caesar(params: CaesarParams, context: MechanicContext) -> Artifact:
    ciphertext: str = shift_letters(plaintext_for(params.plaintext, context, keep_punctuation=True), params.shift)
    key: str = f"A = {ALPHABET[params.shift]}"
    if not params.show_shift:
        return Artifact(html=cipher_html("caesar-cipher", ciphertext), solver_text=f"Ciphertext: {ciphertext}")
    return Artifact(
        html=cipher_html("caesar-cipher", ciphertext, f'<p class="mf-cipher-key">{key}</p>'),
        solver_text=f"Ciphertext: {ciphertext}\nKey: {key}",
    )


def decode_caesar(rendered: RenderedArtifact, params: CaesarParams, context: MechanicContext) -> str:
    return shift_letters(rendered_ciphertext(rendered), -params.shift)


class PlaintextOnlyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION)


def atbash_letters(text: str) -> str:
    return "".join(
        ALPHABET[25 - ALPHABET.index(character)] if character in LETTERS else character for character in text
    )


def build_atbash(params: PlaintextOnlyParams, context: MechanicContext) -> Artifact:
    ciphertext: str = atbash_letters(plaintext_for(params.plaintext, context, keep_punctuation=True))
    return Artifact(html=cipher_html("atbash-cipher", ciphertext), solver_text=f"Ciphertext: {ciphertext}")


def decode_atbash(rendered: RenderedArtifact, params: PlaintextOnlyParams, context: MechanicContext) -> str:
    return atbash_letters(rendered_ciphertext(rendered))


def encode_tokens(plaintext: str, token_for: Mapping[str, str], letter_separator: str) -> str:
    """Write one token per character, `letter_separator` between tokens, and ' / ' between words."""
    return " / ".join(
        letter_separator.join(token_for[character] for character in word) for word in plaintext.split(" ")
    )


def decode_tokens(ciphertext: str, character_for: Mapping[str, str], letter_separator: str) -> str:
    """Reverse `encode_tokens`. A token that no character has becomes '?', so a damaged rendering fails the check."""
    words: list[str] = [word.strip() for word in ciphertext.split("/")]
    return " ".join(
        "".join(character_for.get(token.strip(), "?") for token in word.split(letter_separator)) for word in words
    )


A1Z26_NUMBERS: dict[str, str] = {letter: str(position) for position, letter in enumerate(ALPHABET, start=1)}


def build_a1z26(params: PlaintextOnlyParams, context: MechanicContext) -> Artifact:
    plaintext: str = plaintext_for(params.plaintext, context, keep_punctuation=False)
    require_no_digits(plaintext, "A1Z26")
    ciphertext: str = encode_tokens(plaintext, A1Z26_NUMBERS, "-")
    return Artifact(html=cipher_html("a1z26-cipher", ciphertext), solver_text=f"Ciphertext: {ciphertext}")


def decode_a1z26(rendered: RenderedArtifact, params: PlaintextOnlyParams, context: MechanicContext) -> str:
    return decode_tokens(rendered_ciphertext(rendered), inverted(A1Z26_NUMBERS), "-")


def inverted(mapping: Mapping[str, str]) -> dict[str, str]:
    return {value: key for key, value in mapping.items()}


class VigenereParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION)
    keyword: str = Field(
        description="The secret word that the players must find elsewhere in the game. Letters only, no spaces."
    )


def keyword_shifts(keyword: str) -> list[int]:
    folded: str = fold_text(keyword, keep_punctuation=False)
    if not folded or any(character not in LETTERS for character in folded):
        raise MechanicBuildError(
            f"The Vigenere keyword '{keyword}' must be letters only (A-Z).",
            fix_hint="Use a keyword of one word with letters only, such as a name from the story.",
        )
    return [ALPHABET.index(character) for character in folded]


def vigenere_letters(text: str, shifts: list[int], direction: int) -> str:
    """Shift each letter by the next keyword letter. Only letters use up a keyword letter."""
    result: list[str] = []
    position: int = 0
    for character in text:
        if character in LETTERS:
            result.append(shift_letters(character, direction * shifts[position % len(shifts)]))
            position += 1
        else:
            result.append(character)
    return "".join(result)


def build_vigenere(params: VigenereParams, context: MechanicContext) -> Artifact:
    plaintext: str = plaintext_for(params.plaintext, context, keep_punctuation=True)
    ciphertext: str = vigenere_letters(plaintext, keyword_shifts(params.keyword), 1)
    return Artifact(html=cipher_html("vigenere-cipher", ciphertext), solver_text=f"Ciphertext: {ciphertext}")


def decode_vigenere(rendered: RenderedArtifact, params: VigenereParams, context: MechanicContext) -> str:
    return vigenere_letters(rendered_ciphertext(rendered), keyword_shifts(params.keyword), -1)


MORSE_CODES: dict[str, str] = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..",
    "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}  # fmt: skip


class MorseParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION + " Punctuation is dropped.")
    include_reference_chart: bool = Field(
        default=False, description="Print a chart of the Morse code of every letter and digit, for an easy puzzle."
    )


def morse_chart_html() -> str:
    rows: str = "".join(f"<tr><td>{character}</td><td>{code}</td></tr>" for character, code in MORSE_CODES.items())
    return f'<table class="mf-morse-chart">{rows}</table>'


def build_morse(params: MorseParams, context: MechanicContext) -> Artifact:
    ciphertext: str = encode_tokens(plaintext_for(params.plaintext, context, keep_punctuation=False), MORSE_CODES, " ")
    solver_text: str = f"Morse code: {ciphertext}"
    if not params.include_reference_chart:
        return Artifact(html=cipher_html("morse-code", ciphertext), solver_text=solver_text)
    chart_text: str = ", ".join(f"{character} {code}" for character, code in MORSE_CODES.items())
    return Artifact(
        html=cipher_html("morse-code", ciphertext, morse_chart_html()),
        solver_text=f"{solver_text}\nReference chart: {chart_text}",
    )


def decode_morse(rendered: RenderedArtifact, params: MorseParams, context: MechanicContext) -> str:
    return decode_tokens(rendered_ciphertext(rendered), inverted(MORSE_CODES), " ")


KEYPAD_LETTERS: dict[str, str] = {
    "2": "ABC", "3": "DEF", "4": "GHI", "5": "JKL", "6": "MNO", "7": "PQRS", "8": "TUV", "9": "WXYZ",
}  # fmt: skip
SUPERSCRIPT_DIGITS: str = "⁰¹²³⁴"
MULTITAP_PRESSES: dict[str, str] = {
    letter: key * position
    for key, letters in KEYPAD_LETTERS.items()
    for position, letter in enumerate(letters, start=1)
}
POSITION_PRESSES: dict[str, str] = {
    letter: key + SUPERSCRIPT_DIGITS[position]
    for key, letters in KEYPAD_LETTERS.items()
    for position, letter in enumerate(letters, start=1)
}


class PhoneKeypadParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(
        default=None, description=PLAINTEXT_DESCRIPTION + " Letters only: spell numbers as words."
    )
    style: Literal["multitap", "position"] = Field(
        default="multitap",
        description="'multitap': press the key once per letter position (C = 222). "
        "'position': the key and the letter position as a superscript (C = 2³).",
    )


def presses_for(style: str) -> dict[str, str]:
    return MULTITAP_PRESSES if style == "multitap" else POSITION_PRESSES


def build_phone_keypad(params: PhoneKeypadParams, context: MechanicContext) -> Artifact:
    plaintext: str = plaintext_for(params.plaintext, context, keep_punctuation=False)
    require_no_digits(plaintext, "the phone keypad")
    ciphertext: str = encode_tokens(plaintext, presses_for(params.style), "-")
    return Artifact(html=cipher_html("phone-keypad", ciphertext), solver_text=f"Phone keypad code: {ciphertext}")


def decode_phone_keypad(rendered: RenderedArtifact, params: PhoneKeypadParams, context: MechanicContext) -> str:
    return decode_tokens(rendered_ciphertext(rendered), inverted(presses_for(params.style)), "-")


NATO_WORDS: dict[str, str] = {
    "A": "Alfa", "B": "Bravo", "C": "Charlie", "D": "Delta", "E": "Echo", "F": "Foxtrot", "G": "Golf", "H": "Hotel",
    "I": "India", "J": "Juliett", "K": "Kilo", "L": "Lima", "M": "Mike", "N": "November", "O": "Oscar", "P": "Papa",
    "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango", "U": "Uniform", "V": "Victor", "W": "Whiskey",
    "X": "X-ray", "Y": "Yankee", "Z": "Zulu", "0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
    "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine",
}  # fmt: skip


class NatoParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(default=None, description=PLAINTEXT_DESCRIPTION + " Punctuation is dropped.")
    scramble: bool = Field(
        default=False,
        description="Print the NATO words in a random order, each with its position number (such as '3. Lima'). "
        "The word breaks are lost.",
    )


def build_nato(params: NatoParams, context: MechanicContext) -> Artifact:
    plaintext: str = plaintext_for(params.plaintext, context, keep_punctuation=False)
    if not params.scramble:
        ciphertext: str = encode_tokens(plaintext, NATO_WORDS, " ")
        return Artifact(html=cipher_html("nato-alphabet", ciphertext), solver_text=f"NATO alphabet: {ciphertext}")
    characters: str = plaintext.replace(" ", "")
    order: list[int] = cyclic_permutation(len(characters), random.Random(context.seed))
    entries: list[str] = [f"{index + 1}. {NATO_WORDS[characters[index]]}" for index in order]
    items: str = "".join(f'<li class="mf-nato-entry">{escape_text(entry)}</li>' for entry in entries)
    return Artifact(
        html=f'<div class="mf-cipher mf-nato-alphabet"><ul class="mf-nato-list">{items}</ul></div>',
        solver_text="NATO words with their positions: " + "; ".join(entries),
    )


def decode_nato(rendered: RenderedArtifact, params: NatoParams, context: MechanicContext) -> str:
    character_for: dict[str, str] = inverted(NATO_WORDS)
    if not params.scramble:
        return decode_tokens(rendered_ciphertext(rendered), character_for, " ")
    positioned: list[tuple[int, str]] = []
    for entry in marked_texts(rendered.html, "mf-nato-entry"):
        position, _, word = entry.partition(". ")
        positioned.append((int(position) if position.isdigit() else 0, character_for.get(word.strip(), "?")))
    return "".join(character for _, character in sorted(positioned))


class MirrorParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(
        default=None,
        description="The text to print mirrored. It must contain the answer. Leave it empty to print the answer alone. "
        "The text keeps its case and accents.",
    )


def build_mirror(params: MirrorParams, context: MechanicContext) -> Artifact:
    plaintext_for(params.plaintext, context, keep_punctuation=True)
    # The page shows the agent's own text: a mirror reverses the shapes, so the case and the accents stay readable.
    text: str = " ".join((context.answer if params.plaintext is None else params.plaintext).split())
    return Artifact(
        html=f'<div class="mf-cipher mf-mirror-writing"><p class="mf-mirror">{escape_text(text)}</p></div>',
        solver_text=f"Mirror-reversed text (it reads correctly in a mirror): {text[::-1]}",
    )


def decode_mirror(rendered: RenderedArtifact, params: MirrorParams, context: MechanicContext) -> str:
    return " ".join(marked_texts(rendered.html, "mf-mirror"))


class CryptogramParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plaintext: str | None = Field(
        default=None,
        description=PLAINTEXT_DESCRIPTION + " Write a long message: players work out the letters from repeats.",
    )
    revealed_letters: list[str] = Field(
        default_factory=list,
        description="Plaintext letters that the key gives away from the start, such as ['E', 'T']. Every answer "
        "letter must appear at least twice in the plaintext or be revealed.",
    )


def substitution_alphabet(seed: int) -> dict[str, str]:
    order: list[int] = cyclic_permutation(26, random.Random(seed))
    return {ALPHABET[index]: ALPHABET[order[index]] for index in range(26)}


def revealed_plain_letters(revealed_letters: list[str]) -> list[str]:
    letters: list[str] = []
    for raw_letter in revealed_letters:
        letter: str = fold_text(raw_letter, keep_punctuation=False)
        if len(letter) != 1 or letter not in LETTERS:
            raise MechanicBuildError(
                f"The revealed letter '{raw_letter}' is not one letter A-Z.",
                fix_hint="List single letters in revealed_letters, such as ['E', 'T'].",
            )
        letters.append(letter)
    return letters


def require_decodable_answer(plaintext: str, revealed: list[str], context: MechanicContext) -> None:
    answer_letters: set[str] = {character for character in context.normalized_answer.upper() if character in LETTERS}
    unsolvable: list[str] = sorted(
        letter for letter in answer_letters if plaintext.count(letter) < 2 and letter not in revealed
    )
    if unsolvable:
        raise MechanicBuildError(
            f"These answer letters appear only once in the plaintext and are not revealed: {', '.join(unsolvable)}.",
            fix_hint="Add those letters to revealed_letters, or write a plaintext that uses each of them twice.",
        )


def build_cryptogram(params: CryptogramParams, context: MechanicContext) -> Artifact:
    plaintext: str = plaintext_for(params.plaintext, context, keep_punctuation=True)
    revealed: list[str] = revealed_plain_letters(params.revealed_letters)
    require_decodable_answer(plaintext, revealed, context)
    cipher_for: dict[str, str] = substitution_alphabet(context.seed)
    ciphertext: str = "".join(cipher_for.get(character, character) for character in plaintext)
    if not revealed:
        return Artifact(html=cipher_html("cryptogram", ciphertext), solver_text=f"Ciphertext: {ciphertext}")
    key: str = ", ".join(f"{cipher_for[letter]} = {letter}" for letter in revealed)
    return Artifact(
        html=cipher_html("cryptogram", ciphertext, f'<p class="mf-cipher-key">{key}</p>'),
        solver_text=f"Ciphertext: {ciphertext}\nKnown letters: {key}",
    )


def decode_cryptogram(rendered: RenderedArtifact, params: CryptogramParams, context: MechanicContext) -> str:
    plain_for: dict[str, str] = inverted(substitution_alphabet(context.seed))
    return "".join(plain_for.get(character, character) for character in rendered_ciphertext(rendered))


IMPLEMENTATIONS: tuple[MechanicImplementation[Any], ...] = (
    MechanicImplementation(
        id="caesar-cipher", params_model=CaesarParams, build=build_caesar, decode_rendered=decode_caesar
    ),
    MechanicImplementation(
        id="atbash-cipher", params_model=PlaintextOnlyParams, build=build_atbash, decode_rendered=decode_atbash
    ),
    MechanicImplementation(
        id="a1z26-cipher", params_model=PlaintextOnlyParams, build=build_a1z26, decode_rendered=decode_a1z26
    ),
    MechanicImplementation(
        id="vigenere-cipher", params_model=VigenereParams, build=build_vigenere, decode_rendered=decode_vigenere
    ),
    MechanicImplementation(id="morse-code", params_model=MorseParams, build=build_morse, decode_rendered=decode_morse),
    MechanicImplementation(
        id="phone-keypad",
        params_model=PhoneKeypadParams,
        build=build_phone_keypad,
        decode_rendered=decode_phone_keypad,
    ),
    MechanicImplementation(id="nato-alphabet", params_model=NatoParams, build=build_nato, decode_rendered=decode_nato),
    MechanicImplementation(
        id="mirror-writing", params_model=MirrorParams, build=build_mirror, decode_rendered=decode_mirror
    ),
    MechanicImplementation(
        id="cryptogram", params_model=CryptogramParams, build=build_cryptogram, decode_rendered=decode_cryptogram
    ),
)
