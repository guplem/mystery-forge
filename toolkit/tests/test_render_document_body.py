from mystery_forge.mechanics.base import Artifact
from mystery_forge.render.document_body import (
    SpeakerLine,
    clean_svg,
    insert_artifacts,
    insert_images,
    speaker_lines,
    split_pages,
)
from mystery_forge.spec.documents import render_markdown


def test_split_pages_cuts_at_each_page_break_and_drops_empty_pages() -> None:
    body = render_markdown("One\n\n::: pagebreak\n:::\n\nTwo\n\n::: pagebreak\n:::\n", "D1.md", 1).html
    assert split_pages(body) == ["<p>One</p>\n", "<p>Two</p>\n"]
    assert split_pages("") == [""]


def test_insert_artifacts_replaces_the_paragraph_mark_and_adds_the_print_notes() -> None:
    artifact = Artifact(html="<p class='mf-cipher'>NHBV</p>", solver_text="x", print_notes=("Cut <out> the strips",))
    html = insert_artifacts("<p>Intro</p>\n<p>⟦artifact:P1⟧</p>\n", {"P1": artifact})
    assert '<div class="mf-artifact-block">' in html
    assert "<p>⟦" not in html
    assert '<div class="mf-artifact" data-artifact="P1"><p class=\'mf-cipher\'>NHBV</p></div>' in html
    assert '<li class="mf-print-note">' in html
    assert "Cut &lt;out&gt; the strips" in html


def test_insert_artifacts_handles_an_inline_mark_and_a_missing_artifact() -> None:
    html = insert_artifacts("<p>See ⟦artifact:P2⟧ here</p>", {"P2": None})
    assert '<div class="mf-artifact mf-artifact-missing" data-artifact="P2"></div>' in html
    assert "mf-print-notes" not in html


def test_insert_images_wraps_the_svg_in_a_figure_with_its_caption() -> None:
    images = {"lamp": '<?xml version="1.0"?>\n<!DOCTYPE svg>\n<svg viewBox="0 0 1 1"><script>x()</script></svg>'}
    html = insert_images("<p>⟦image:lamp|The lamp &amp; room⟧</p>\n", images)
    assert html.startswith('<figure class="mf-figure" data-image="lamp">')
    assert "<figcaption>The lamp &amp; room</figcaption>" in html
    assert "<?xml" not in html and "<script" not in html and "DOCTYPE" not in html
    without_caption = insert_images("<p>Look: ⟦image:lamp|⟧</p>", images)
    assert "figcaption" not in without_caption
    assert "Look: <figure" in without_caption
    unknown = insert_images("<p>⟦image:ghost|Boo⟧</p>", images)
    assert '<div class="mf-figure-art"></div>' in unknown


def test_clean_svg_keeps_a_plain_svg() -> None:
    assert clean_svg("<svg><rect/></svg>") == "<svg><rect/></svg>"


def test_speaker_lines_split_dialogue_and_keep_narration() -> None:
    body = render_markdown(
        "Ana: Where is it?\nBen: **Gone.**\n\nThe line goes quiet.\n\n- a list\n\nTom Bell: Hello: there", "x.md", 1
    ).html
    lines = speaker_lines(body)
    assert lines[0] == SpeakerLine(speaker="Ana", html="Where is it?")
    assert lines[1] == SpeakerLine(speaker="Ben", html="<strong>Gone.</strong>")
    assert lines[2] == SpeakerLine(speaker=None, html="The line goes quiet.")
    assert lines[3].speaker is None and "<li>a list</li>" in lines[3].html
    assert lines[4] == SpeakerLine(speaker="Tom Bell", html="Hello: there")


def test_speaker_lines_ignore_a_colon_after_a_long_sentence() -> None:
    lines = speaker_lines("<p>This is a whole sentence that is far too long to be a name: yes</p>")
    assert lines == [SpeakerLine(speaker=None, html="This is a whole sentence that is far too long to be a name: yes")]


def test_speaker_lines_keep_a_block_after_the_last_paragraph() -> None:
    lines = speaker_lines("<p>Ana: Hi</p>\n<ul>\n<li>note</li>\n</ul>\n")
    assert lines == [
        SpeakerLine(speaker="Ana", html="Hi"),
        SpeakerLine(speaker=None, html="<ul>\n<li>note</li>\n</ul>"),
    ]
