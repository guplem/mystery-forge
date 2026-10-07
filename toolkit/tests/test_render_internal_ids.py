from test_render_support import golden_game

from mystery_forge.render.internal_ids import printed_ids


def test_puzzle_ids_become_codes_and_document_ids_become_titles() -> None:
    assert printed_ids(golden_game(), "Solve P1 first, then read D3 and P3.") == (
        "Solve A1 first, then read The supply receipt and B1."
    )


def test_unknown_ids_and_longer_words_stay() -> None:
    assert printed_ids(golden_game(), "P9, D99, MP3, P1a and DP1 stay.") == "P9, D99, MP3, P1a and DP1 stay."
