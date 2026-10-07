"""The solver panel must test the printed game, so a solver text shows what the sheet prints and never the method."""

from typing import Any

import pytest

from mystery_forge.mechanics.base import Artifact, MechanicContext, MechanicImplementation, parse_params
from mystery_forge.mechanics.registry import all_implementations

IMPLEMENTATIONS: dict[str, MechanicImplementation[Any]] = dict(all_implementations())

# Words that name a method or a mechanic, or a label that no printed sheet shows.
METHOD_WORDS: tuple[str, ...] = (
    "cipher", "caesar", "atbash", "vigenere", "cryptogram", "morse", "keypad", "phone", "nato", "alphabet",
    "mirror", "pigpen", "braille", "anagram", "tiles", "reference chart", "known letters", "words:", "grid:",
    "mask (", "coordinates", "clues:", "question:", "enter at",
)  # fmt: skip

CASES: list[tuple[str, dict[str, Any], str]] = [
    ("caesar-cipher", {"shift": 5, "show_shift": True, "plaintext": "Meet at the old mill."}, "mill"),
    ("atbash-cipher", {"plaintext": "Meet at the old mill."}, "mill"),
    ("a1z26-cipher", {"plaintext": "Meet at the old mill."}, "mill"),
    ("vigenere-cipher", {"keyword": "Lemon", "plaintext": "Meet at the old mill."}, "mill"),
    ("morse-code", {"include_reference_chart": True, "plaintext": "Meet at the old mill."}, "mill"),
    ("phone-keypad", {"plaintext": "Meet at the old mill."}, "mill"),
    ("nato-alphabet", {"plaintext": "Meet at the old mill."}, "mill"),
    ("nato-alphabet", {"scramble": True, "plaintext": "Meet at the old mill."}, "mill"),
    ("mirror-writing", {"plaintext": "Meet at the old mill."}, "mill"),
    ("cryptogram", {"revealed_letters": ["O", "D", "M", "I"], "plaintext": "Meet at the old mill."}, "mill"),
    ("pigpen-cipher", {"include_key": True, "plaintext": "Old mill"}, "mill"),
    ("braille", {"include_key": True, "plaintext": "Old mill"}, "mill"),
    ("symbol-substitution", {"plaintext": "Old mill"}, "mill"),
    ("anagram", {"letters": "Llim"}, "mill"),
    (
        "word-search",
        {
            "words": [
                "anchor",
                "beacon",
                "harbor",
                "island",
                "ocean",
                "pirate",
                "sailor",
                "ship",
                "storm",
                "tide",
                "wave",
            ]
        },
        "Lighthouse",
    ),
    ("overlay-mask", {}, "mill"),
    ("grid-coordinates", {}, "mill"),
    ("maze", {}, "mill"),
    (
        "logic-grid",
        {
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
        },
        "tea",
    ),
]


def build(mechanic: str, params: dict[str, Any], answer: str) -> Artifact:
    implementation: MechanicImplementation[Any] = IMPLEMENTATIONS[mechanic]
    context = MechanicContext(puzzle_id="P1", answer=answer, language="en", seed=7, documents={})
    return implementation.build(parse_params(implementation, params), context)


@pytest.mark.parametrize(("mechanic", "params", "answer"), CASES)
def test_a_solver_text_never_names_the_method(mechanic: str, params: dict[str, Any], answer: str) -> None:
    text: str = build(mechanic, params, answer).solver_text.casefold()
    assert text
    assert [word for word in METHOD_WORDS if word in text] == []
