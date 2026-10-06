import pytest

from mystery_forge.yaml_loading import YamlLoadError, parse_yaml_text, split_front_matter


def test_every_scalar_stays_text_except_null() -> None:
    document = parse_yaml_text("answer: 0420\nok: no\nshift: 3\nwhen: 2026-01-02\nempty: null\ntilde: ~\n", "a.yaml")
    assert document.data == {
        "answer": "0420",
        "ok": "no",
        "shift": "3",
        "when": "2026-01-02",
        "empty": None,
        "tilde": None,
    }


def test_quoted_null_stays_text() -> None:
    assert parse_yaml_text('value: "null"\n', "a.yaml").data == {"value": "null"}


def test_lines_are_recorded_for_every_path() -> None:
    text = "title: X\npuzzles:\n  - id: P1\n    hints:\n      - one\n"
    document = parse_yaml_text(text, "a.yaml")
    assert document.line_of(("title",)) == 1
    assert document.line_of(("puzzles", 0, "id")) == 3
    assert document.line_of(("puzzles", 0, "hints", 0)) == 5
    assert document.line_of(("missing",)) is None
    assert document.line_of(("puzzles", 0, "hints", 9)) == 5


def test_an_empty_document_is_none() -> None:
    assert parse_yaml_text("", "a.yaml").data is None


def test_a_duplicate_key_is_an_error_with_its_line() -> None:
    with pytest.raises(YamlLoadError) as raised:
        parse_yaml_text("a: 1\nb: 2\na: 3\n", "dup.yaml")
    assert raised.value.line == 3
    assert "a" in raised.value.message
    assert raised.value.source == "dup.yaml"


def test_a_syntax_error_reports_its_line() -> None:
    with pytest.raises(YamlLoadError) as raised:
        parse_yaml_text("a: [1, 2\nb: 3\n", "bad.yaml")
    assert raised.value.line is not None
    assert "bad.yaml" in str(raised.value)


def test_a_non_text_key_is_an_error() -> None:
    with pytest.raises(YamlLoadError, match="key"):
        parse_yaml_text("? [a, b]\n: c\n", "key.yaml")


def test_aliases_resolve_to_the_same_value() -> None:
    document = parse_yaml_text("base: &b {x: 1}\ncopy: *b\n", "alias.yaml")
    assert document.data == {"base": {"x": "1"}, "copy": {"x": "1"}}


def test_split_front_matter_returns_the_header_the_body_and_the_body_line() -> None:
    header, body, body_line = split_front_matter("---\nid: D1\nkind: letter\n---\nDear Ana,\n\nHello.\n")
    assert header == "id: D1\nkind: letter\n"
    assert body == "Dear Ana,\n\nHello.\n"
    assert body_line == 5


def test_split_front_matter_without_a_header() -> None:
    assert split_front_matter("Just text\n") == (None, "Just text\n", 1)


def test_split_front_matter_with_an_unclosed_header_is_an_error() -> None:
    with pytest.raises(YamlLoadError, match="front matter"):
        split_front_matter("---\nid: D1\nno closing line\n")


def test_split_front_matter_accepts_windows_line_endings() -> None:
    header, body, body_line = split_front_matter("---\r\nid: D1\r\n---\r\nText\r\n")
    assert header == "id: D1\n"
    assert body == "Text\n"
    assert body_line == 4
