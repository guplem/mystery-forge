from pathlib import Path

import pytest

from mystery_forge.spec.documents import (
    ARTIFACT_MARK,
    IMAGE_MARK,
    ReferenceContext,
    html_to_text,
    render_markdown,
    resolve_references,
)
from mystery_forge.spec.loader import load_game_source

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


@pytest.fixture(scope="module")
def context() -> ReferenceContext:
    source, findings = load_game_source(GOLDEN_GAME)
    assert findings == []
    assert source.story is not None
    return ReferenceContext(
        language="es",
        story=source.story,
        stage_ids=frozenset({"A", "B"}),
        document_titles={document.meta.id: document.meta.title for document in source.documents},
        puzzle_ids=frozenset({"P1", "P2", "P3"}),
        image_ids=frozenset({"lamp"}),
    )


def resolve(body: str, context: ReferenceContext, owner: str | None = None) -> tuple[str, list[str]]:
    resolved, findings = resolve_references(body, owner, context, "documents/D9.md", 10)
    return resolved, [finding.rule for finding in findings]


def test_registry_references_resolve_to_names_and_fields(context: ReferenceContext) -> None:
    resolved, rules = resolve(
        "{{char:ana-ruiz}} ({{char:ana-ruiz.role}}, {{char:ana-ruiz.age}}) in {{place:kitchen}} with {{object:great-lens}}.",
        context,
    )
    assert rules == []
    assert resolved == "Ana Ruiz (cook, 34) in the kitchen with the great lens."


def test_event_references_format_dates_times_and_weekdays_in_the_game_language(context: ReferenceContext) -> None:
    resolved, rules = resolve("{{event:delivery.date}} {{event:delivery.time}} {{event:delivery.weekday}}", context)
    assert rules == []
    assert resolved == "14 de marzo de 1931 18:00 sábado"


def test_document_stage_and_name_references(context: ReferenceContext) -> None:
    resolved, rules = resolve("See {{doc:D3}} in {{stage:B}}. {{char:felix-ward.description}}", context)
    assert rules == []
    assert resolved == "See The supply receipt in Sobre B. He brings oil, flour, and rope to the rock once a week."


def test_artifact_and_image_references_become_marks(context: ReferenceContext) -> None:
    resolved, rules = resolve(
        "{{artifact}} {{artifact:P2}} {{image:lamp}} {{image:lamp|The lamp at night}}", context, "P1"
    )
    assert rules == []
    assert resolved == (
        f"{ARTIFACT_MARK.format(puzzle='P1')} {ARTIFACT_MARK.format(puzzle='P2')} "
        f"{IMAGE_MARK.format(image='lamp', caption='')} {IMAGE_MARK.format(image='lamp', caption='The lamp at night')}"
    )


@pytest.mark.parametrize(
    "body",
    [
        "{{char:nobody}}",
        "{{char:ana-ruiz.shoe_size}}",
        "{{place:moon}}",
        "{{object:spoon}}",
        "{{event:party.date}}",
        "{{event:delivery.color}}",
        "{{doc:D99}}",
        "{{stage:Z}}",
        "{{artifact:P9}}",
        "{{image:missing}}",
        "{{weird:thing}}",
        "{{artifact}}",
    ],
)
def test_unknown_references_are_findings_with_the_line(body: str, context: ReferenceContext) -> None:
    resolved, findings = resolve_references(f"Line one\n{body}", None, context, "documents/D9.md", 10)
    assert [finding.rule for finding in findings] == ["reference.unknown"]
    assert findings[0].line == 11
    assert findings[0].fix_hint
    assert body in resolved


def test_a_character_without_an_age_is_a_finding(context: ReferenceContext) -> None:
    story = context.story.model_copy(
        update={"characters": [context.story.characters[0].model_copy(update={"age": None})]}
    )
    no_age = ReferenceContext(
        language="en",
        story=story,
        stage_ids=context.stage_ids,
        document_titles=context.document_titles,
        puzzle_ids=context.puzzle_ids,
        image_ids=context.image_ids,
    )
    _, rules = resolve("{{char:tom-bell.age}}", no_age)
    assert rules == ["reference.unknown"]


def test_render_markdown_turns_directives_into_styled_blocks() -> None:
    rendered = render_markdown(
        "Hello **there**.\n\n::: handwriting\nE. Lowe\n:::\n\n::: stamp\nCONFIDENTIAL\n:::\n\n"
        "::: pagebreak\n:::\n\n::: redacted\nsecret words\n:::\n",
        "documents/D1.md",
        5,
    )
    assert rendered.findings == []
    assert '<div class="mf-handwriting">' in rendered.html
    assert '<div class="mf-stamp">' in rendered.html
    assert '<div class="mf-pagebreak"></div>' in rendered.html
    assert "secret words" not in rendered.html
    assert '<span class="mf-redacted">' in rendered.html
    assert rendered.text == "Hello there.\n\nE. Lowe\n\nCONFIDENTIAL\n\n████████████"


def test_render_markdown_reports_unknown_directives_with_their_line() -> None:
    rendered = render_markdown("Text\n\n::: sparkle\nShiny\n:::\n", "documents/D1.md", 5)
    assert [finding.rule for finding in rendered.findings] == ["document.unknown_directive"]
    assert rendered.findings[0].line == 7


def test_render_markdown_escapes_raw_html() -> None:
    rendered = render_markdown("<script>alert(1)</script> & more", "documents/D1.md", 1)
    assert "<script>" not in rendered.html
    assert "&lt;script&gt;" in rendered.html
    assert rendered.text == "<script>alert(1)</script> & more"


def test_html_to_text_separates_blocks_and_collapses_spaces() -> None:
    assert html_to_text("<h1>Title</h1><p>One   two</p><ul><li>a</li><li>b</li></ul><p>x<br>y</p>") == (
        "Title\n\nOne two\n\na\n\nb\n\nx\ny"
    )
    assert html_to_text("<table><tr><td>A</td><td>B</td></tr><tr><td>C</td></tr></table>") == "A B\nC"
    assert html_to_text("") == ""
