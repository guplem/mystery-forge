from datetime import datetime

import pytest

from mystery_forge.i18n import LANGUAGES, format_date, text, weekday_name


def test_every_language_has_every_key_of_english() -> None:
    from mystery_forge.i18n import STRINGS

    english_keys = set(STRINGS["en"])
    for language in LANGUAGES:
        assert set(STRINGS[language]) == english_keys, language


def test_text_returns_the_string_of_the_language_and_formats_values() -> None:
    assert text("es", "envelope_label", stage="B") == "Sobre B"
    assert text("en", "envelope_label", stage="B") == "Envelope B"


def test_text_falls_back_to_english_for_an_unknown_language() -> None:
    assert text("xx", "envelope_label", stage="C") == "Envelope C"


def test_text_rejects_an_unknown_key() -> None:
    with pytest.raises(KeyError, match="no_such_key"):
        text("en", "no_such_key")


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "14 March 1931"),
        ("es", "14 de marzo de 1931"),
        ("ca", "14 de març de 1931"),
        ("fr", "14 mars 1931"),
        ("de", "14. März 1931"),
        ("it", "14 marzo 1931"),
        ("pt", "14 de março de 1931"),
        ("xx", "14 March 1931"),
    ],
)
def test_format_date_uses_the_language(language: str, expected: str) -> None:
    assert format_date(datetime(1931, 3, 14), language) == expected


def test_weekday_name_uses_the_language() -> None:
    saturday = datetime(1931, 3, 14)
    assert weekday_name(saturday, "en") == "Saturday"
    assert weekday_name(saturday, "es") == "sábado"
    assert weekday_name(saturday, "xx") == "Saturday"
