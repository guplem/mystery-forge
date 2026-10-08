from test_checks_support import edit_document, golden_game, rules

from mystery_forge.checks.calendar import check_calendar
from mystery_forge.game import Game
from mystery_forge.i18n import language_pack_template, register_language


def japanese(date_pattern: str) -> Game:
    register_language("ja", language_pack_template().model_copy(update={"date_pattern": date_pattern}))
    game = golden_game()
    return game.model_copy(update={"config": game.config.model_copy(update={"language": "ja"})})


def test_an_era_year_in_a_game_that_prints_western_years_is_an_error(restored_tables: None) -> None:
    game = edit_document(
        japanese("{year}年{month}{day}日"), "D1", text=f"祖父は昭和{chr(0xFF11)}{chr(0xFF12)}年に生まれた。"
    )
    findings = check_calendar(game)
    assert rules(findings) == ["dates.mixed_year_style"]
    assert (findings[0].file, findings[0].severity) == ("documents/D1.md", "error")
    assert f"'昭和{chr(0xFF11)}{chr(0xFF12)}年'" in findings[0].message
    assert check_calendar(edit_document(game, "D1", text="祖父は1937年に生まれた。")) == []


def test_a_western_year_in_a_game_that_prints_era_years_is_an_error(restored_tables: None) -> None:
    game = edit_document(japanese("{era_year}年{month}{day}日"), "D1", text="1958年の冬、雪が降った。")
    assert rules(check_calendar(game)) == ["dates.mixed_year_style"]
    assert check_calendar(edit_document(game, "D1", text="昭和元年の冬と昭和33年の夏。")) == []
    # A number with more digits is no year, such as a price.
    assert check_calendar(edit_document(game, "D1", text="代金は12000年分ではない。")) == []


def test_the_golden_game_has_one_year_style() -> None:
    assert check_calendar(golden_game()) == []
