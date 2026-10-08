from datetime import datetime

import pytest

from mystery_forge.i18n import (
    LANGUAGES,
    LanguagePack,
    format_date,
    language_pack_problems,
    language_pack_template,
    register_language,
    text,
    text_direction,
    weekday_name,
)


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


def test_a_solo_game_gets_the_solo_text_when_one_exists() -> None:
    assert text("es", "cover_players", solo=True, count="1") == "1 jugador"
    assert text("es", "cover_players", count="1") == "1 jugadores"
    assert text("en", "accusation_title", solo=True) == "Accusation form"


def japanese_pack() -> LanguagePack:
    template = language_pack_template()
    strings = {key: f"JA {value}" for key, value in template.strings.items()}
    return LanguagePack(
        strings=strings,
        months=[f"{number}月" for number in range(1, 13)],
        weekdays=["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
        date_pattern="{year}年{month}{day}日",
    )


def test_the_template_holds_every_english_text_and_the_calendar() -> None:
    template = language_pack_template()
    assert template.strings["envelope_label"] == "Envelope {stage}"
    assert template.months[0] == "January" and len(template.months) == 12
    assert template.weekdays[-1] == "Sunday" and len(template.weekdays) == 7
    assert template.date_pattern == "{day} {month} {year}"
    assert language_pack_problems(template) == []


def test_a_pack_must_keep_every_key_and_every_placeholder() -> None:
    template = language_pack_template()
    strings = dict(template.strings)
    del strings["continued"]
    strings["envelope_label"] = "Sobre {etapa}"
    strings["made_up_key"] = "x"
    broken = template.model_copy(update={"strings": strings, "date_pattern": "{day} {month}"})
    assert language_pack_problems(broken) == [
        "The key 'continued' is missing.",
        "The key 'made_up_key' is not a fixed text.",
        "The text 'envelope_label' must keep the fields {stage}, not {etapa}.",
        "The date pattern must hold {day}, {month}, and {year} (or {era_year}, the Japanese era year).",
    ]
    era = template.model_copy(update={"date_pattern": "{era_year}年{month}{day}日"})
    assert language_pack_problems(era) == []


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(1958, 3, 14), "昭和33"),
        (datetime(1926, 12, 24), "大正15"),
        (datetime(1926, 12, 25), "昭和元"),
        (datetime(1989, 1, 8), "平成元"),
        (datetime(2019, 5, 1), "令和元"),
        (datetime(1912, 7, 29), "明治45"),
        (datetime(1850, 1, 1), "1850"),
    ],
)
def test_a_date_pattern_may_print_the_japanese_era_year(restored_tables: None, moment: datetime, expected: str) -> None:
    pack = language_pack_template().model_copy(update={"date_pattern": "{era_year}年{month}{day}日"})
    pack = pack.model_copy(update={"months": [f"{number}月" for number in range(1, 13)]})
    register_language("ja", pack)
    assert format_date(moment, "ja") == f"{expected}年{moment.month}月{moment.day}日"


def test_a_registered_pack_serves_its_language(restored_tables: None) -> None:
    register_language("ja", japanese_pack())
    assert text("ja", "envelope_label", stage="B") == "JA Envelope B"
    assert format_date(datetime(1931, 3, 14), "ja") == "1931年3月14日"
    assert weekday_name(datetime(1931, 3, 14), "ja") == "土曜日"


def test_a_translated_file_name_may_not_hold_a_character_that_file_names_forbid() -> None:
    template = language_pack_template()
    strings = dict(template.strings)
    strings["file_manual"] = "1 - Start: here?"
    problems = language_pack_problems(template.model_copy(update={"strings": strings}))
    assert problems == ["The file name 'file_manual' holds a character that file names forbid: ':', '?'."]


def test_arabic_hebrew_persian_and_urdu_read_from_right_to_left() -> None:
    assert [text_direction(language) for language in ("ar", "he", "fa", "ur", "en", "ja")] == [
        "rtl",
        "rtl",
        "rtl",
        "rtl",
        "ltr",
        "ltr",
    ]


def test_join_list_follows_the_language() -> None:
    from mystery_forge.i18n import join_list

    assert join_list("en", []) == ""
    assert join_list("en", ["a"]) == "a"
    assert join_list("en", ["a", "b"]) == "a and b"
    assert join_list("en", ["a", "b", "c"]) == "a, b, and c"
    assert join_list("ca", ["a", "b", "c"]) == "a, b i c"
