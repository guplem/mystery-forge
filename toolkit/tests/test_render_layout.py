import pytest

from mystery_forge.render.layout import (
    SAFE_HEIGHT_MM,
    TIGHTEN_FACTOR,
    page_budget,
    split_text,
    text_height,
    tightness,
)


def test_page_budget_uses_the_paper_and_shrinks_with_each_tightness_level() -> None:
    assert page_budget("A4", 30, 0) == SAFE_HEIGHT_MM["A4"] - 30
    assert page_budget("Letter", 30, 0) == SAFE_HEIGHT_MM["Letter"] - 30
    assert page_budget("A4", 30, 2) == pytest.approx((SAFE_HEIGHT_MM["A4"] - 30) * TIGHTEN_FACTOR**2)


def test_tightness_reads_a_group_level_or_zero() -> None:
    assert tightness({"results": 2}, "results") == 2
    assert tightness({}, "results") == 0


def test_text_height_counts_wrapped_lines_and_line_breaks() -> None:
    assert text_height("", 10, 5) == 5
    assert text_height("x" * 10, 10, 5) == 5
    assert text_height("x" * 11, 10, 5) == 10
    assert text_height("ab\ncd", 10, 5) == 10


def test_split_text_keeps_sentences_together_when_it_can() -> None:
    text = "One two three. Four five six. Seven eight nine."
    assert split_text(text, 100) == [text]
    assert split_text(text, 30) == ["One two three. Four five six.", "Seven eight nine."]


def test_split_text_cuts_a_long_sentence_between_words_and_a_long_word_anywhere() -> None:
    assert split_text("aaa bbb ccc ddd", 7) == ["aaa bbb", "ccc ddd"]
    assert split_text("abcdefghij", 4) == ["abcd", "efgh", "ij"]
    assert split_text("short. " + "x" * 9, 6) == ["short.", "xxxxxx", "xxx"]
    assert split_text("ab abcdefgh", 4) == ["ab", "abcd", "efgh"]
    assert split_text("", 4) == []
