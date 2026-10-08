import pytest

from mystery_forge.text_measure import count_words, display_length


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("The old mill", 3),
        ("  The   old\nmill!  ", 3),
        ("", 0),
        ("— ...", 0),
        # Japanese and Chinese write no spaces: two characters count as one word.
        ("雪に埋もれた郵便袋", 5),
        ("图书馆", 2),
        ("Hello 世界", 2),
        ("東京2026年", 3),
        # Korean writes spaces between its words, so a Hangul word counts once.
        ("오래된 도서관", 2),
        # Thai writes no spaces either; its vowel marks are not letters and do not count.
        ("สวัสดีครับ", 4),
    ],
)
def test_count_words_counts_scripts_without_spaces_by_characters(text: str, words: int) -> None:
    assert count_words(text) == words


@pytest.mark.parametrize(
    ("text", "length"),
    [("abc", 3), ("郵便袋", 6), (chr(0xFF21) + chr(0xFF22), 4), ("a郵", 3), ("오래", 4), ("", 0)],
)
def test_display_length_counts_a_full_width_character_twice(text: str, length: int) -> None:
    assert display_length(text) == length
