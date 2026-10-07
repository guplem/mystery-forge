"""Document bodies: registry references, Markdown with a small fixed set of directives, and plain text.

An agent writes `{{char:ana-ruiz}}` instead of retyping a name, so a name, an age, or a date is the same in every
document (the toolkit computes weekdays and formats dates). Artifacts and images become marks that the renderer
replaces after the Markdown step. The plain text of a document is what the evidence checks and the solver panel read.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Final

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.container import container_plugin

from mystery_forge.findings import Finding
from mystery_forge.i18n import format_date, text, weekday_name
from mystery_forge.spec.models import Story

ARTIFACT_MARK: Final[str] = "⟦artifact:{puzzle}⟧"
IMAGE_MARK: Final[str] = "⟦image:{image}|{caption}⟧"
REDACTED_MARK: Final[str] = "⟦redacted:{length}⟧"
REDACTED_PATTERN: Final[re.Pattern[str]] = re.compile(r"⟦redacted:(\d+)⟧")
REFERENCE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\{\{\s*([a-z]+)(?::([^}|]+?))?(?:\|([^}]*))?\s*\}\}")
REDACTED_BLOCK: Final[re.Pattern[str]] = re.compile(r"^::: *redacted *\n(.*?)\n:::[ \t]*$", re.MULTILINE | re.DOTALL)
DIRECTIVE_LINE: Final[re.Pattern[str]] = re.compile(r"^:::\s*([A-Za-z][\w-]*)")
STYLE_DIRECTIVES: Final[tuple[str, ...]] = ("handwriting", "typewriter", "stamp", "note", "center", "small")
ALL_DIRECTIVES: Final[frozenset[str]] = frozenset({*STYLE_DIRECTIVES, "pagebreak", "redacted"})
REDACTED_CHARACTER: Final[str] = "█"

CHARACTER_FIELDS: Final[tuple[str, ...]] = ("name", "role", "age", "description")
EVENT_FIELDS: Final[tuple[str, ...]] = ("date", "time", "weekday")


@dataclass(frozen=True)
class ReferenceContext:
    """What a reference can point to."""

    language: str
    story: Story
    stage_ids: frozenset[str]
    document_titles: dict[str, str]
    puzzle_ids: frozenset[str]
    image_ids: frozenset[str]


@dataclass(frozen=True)
class RenderedBody:
    html: str
    text: str
    findings: list[Finding]


def resolve_references(
    body: str, owner_puzzle: str | None, context: ReferenceContext, file: str, body_line: int
) -> tuple[str, list[Finding]]:
    """Replace every `{{kind:target}}` reference. An unknown reference stays as it is and gets a finding."""
    findings: list[Finding] = []

    def replace(match: re.Match[str]) -> str:
        kind: str = match.group(1)
        target: str = (match.group(2) or "").strip()
        caption: str = (match.group(3) or "").strip()
        value: str | None = reference_value(kind, target, caption, owner_puzzle, context)
        if value is None:
            line: int = body_line + body.count("\n", 0, match.start())
            findings.append(
                Finding(
                    severity="error",
                    rule="reference.unknown",
                    message=f"The reference '{match.group(0)}' points to nothing.",
                    file=file,
                    line=line,
                    fix_hint="Use an id from story.yaml, flow.yaml, puzzles/, documents/, or images/. "
                    "Run `forge schema references` for the list of reference forms.",
                )
            )
            return match.group(0)
        return value

    return REFERENCE_PATTERN.sub(replace, body), findings


def reference_value(
    kind: str, target: str, caption: str, owner_puzzle: str | None, context: ReferenceContext
) -> str | None:
    if kind == "artifact":
        # `{{artifact:P2.key1}}` prints one part of the material; the graph check knows the part names.
        puzzle, _, part = (target or owner_puzzle or "").partition(".")
        if puzzle not in context.puzzle_ids:
            return None
        return ARTIFACT_MARK.format(puzzle=f"{puzzle}.{part}" if part else puzzle)
    if kind == "image":
        return IMAGE_MARK.format(image=target, caption=caption) if target in context.image_ids else None
    if kind == "doc":
        return context.document_titles.get(target)
    if kind == "stage":
        return text(context.language, "envelope_label", stage=target) if target in context.stage_ids else None
    identifier, _, field = target.partition(".")
    if kind == "char":
        return character_value(identifier, field or "name", context)
    if kind in ("place", "object"):
        entries = context.story.locations if kind == "place" else context.story.objects
        names: dict[str, str] = {entry.id: entry.name for entry in entries}
        return names.get(identifier) if not field else None
    if kind == "event":
        return event_value(identifier, field, context)
    return None


def character_value(identifier: str, field: str, context: ReferenceContext) -> str | None:
    for character in context.story.characters:
        if character.id == identifier and field in CHARACTER_FIELDS:
            value: object = getattr(character, field)
            return None if value is None else str(value)
    return None


def event_value(identifier: str, field: str, context: ReferenceContext) -> str | None:
    for event in context.story.timeline:
        if event.id == identifier and field in EVENT_FIELDS:
            moment: datetime = event.start_time
            if field == "date":
                return format_date(moment, context.language)
            if field == "time":
                return moment.strftime("%H:%M")
            return weekday_name(moment, context.language)
    return None


def build_markdown_parser() -> MarkdownIt:
    parser: MarkdownIt = MarkdownIt("commonmark", {"html": False, "typographer": False}).enable("strikethrough")
    for name in STYLE_DIRECTIVES:
        parser.use(container_plugin, name=name, render=style_container_renderer(name))
    parser.use(container_plugin, name="pagebreak", render=render_pagebreak)
    return parser


def style_container_renderer(name: str) -> object:
    def render(self: object, tokens: list[Token], index: int, options: object, env: object) -> str:
        return f'<div class="mf-{name}">\n' if tokens[index].nesting == 1 else "</div>\n"

    return render


def render_pagebreak(self: object, tokens: list[Token], index: int, options: object, env: object) -> str:
    return '<div class="mf-pagebreak"></div>\n' if tokens[index].nesting == 1 else ""


MARKDOWN: Final[MarkdownIt] = build_markdown_parser()


def render_markdown(resolved_body: str, file: str, body_line: int) -> RenderedBody:
    """Render a resolved body to HTML and to plain text, and report unknown directives."""
    findings: list[Finding] = unknown_directive_findings(resolved_body, file, body_line)
    without_secrets: str = REDACTED_BLOCK.sub(
        lambda match: REDACTED_MARK.format(length=len(match.group(1).strip())), resolved_body
    )
    html: str = MARKDOWN.render(without_secrets)
    html = REDACTED_PATTERN.sub(
        lambda match: f'<span class="mf-redacted">{REDACTED_CHARACTER * int(match.group(1))}</span>', html
    )
    return RenderedBody(html=html, text=html_to_text(html), findings=findings)


def unknown_directive_findings(body: str, file: str, body_line: int) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(body.split("\n")):
        match: re.Match[str] | None = DIRECTIVE_LINE.match(line)
        if match is not None and match.group(1) not in ALL_DIRECTIVES:
            findings.append(
                Finding(
                    severity="error",
                    rule="document.unknown_directive",
                    message=f"The directive '::: {match.group(1)}' does not exist.",
                    file=file,
                    line=body_line + index,
                    fix_hint=f"Use one of: {', '.join(sorted(ALL_DIRECTIVES))}.",
                )
            )
    return findings


BLOCK_TAGS: Final[frozenset[str]] = frozenset(
    {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "table", "blockquote", "pre", "hr", "figure"}
)


class TextExtractor(HTMLParser):
    """Collect the visible text of HTML, with a blank line between blocks, like a browser's innerText."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n\n")
        elif tag == "tr":
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        self.parts.append(re.sub(r"\s+", " ", data))


def html_to_text(html: str) -> str:
    extractor: TextExtractor = TextExtractor()
    extractor.feed(html)
    joined: str = "".join(extractor.parts)
    lines: list[str] = [line.strip() for line in joined.split("\n")]
    collapsed: str = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return collapsed.strip()
