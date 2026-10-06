"""Turn an assembled document body into the HTML of its printed pages.

The assembled body holds marks (`spec/documents.py`) that only the renderer can fill: the built artifact of a puzzle
and the SVG of an image. The checks read each artifact back from the page by its `data-artifact` attribute.
"""

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from mystery_forge.mechanics.base import Artifact

PAGEBREAK: Final[str] = '<div class="mf-pagebreak"></div>\n'
ARTIFACT_MARK_PATTERN: Final[re.Pattern[str]] = re.compile(r"(<p>)?⟦artifact:(P\d+)⟧(</p>)?")
IMAGE_MARK_PATTERN: Final[re.Pattern[str]] = re.compile(r"(<p>)?⟦image:([^|⟧]+)\|([^⟧]*)⟧(</p>)?")
SVG_NOISE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>|<script\b.*?</script>", re.DOTALL | re.IGNORECASE
)
PARAGRAPH_PATTERN: Final[re.Pattern[str]] = re.compile(r"<p>(.*?)</p>\n?", re.DOTALL)
# A speaker name is short and starts the line: "Ana:", "Tom Bell:", "<strong>Inspector</strong>:".
SPEAKER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?:<strong>)?([^<:\n]{1,30}?)(?:</strong>)?:\s*(.+)$", re.DOTALL
)
SCISSORS_ICON: Final[str] = (
    '<svg class="mf-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="6" r="3"/>'
    '<circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/></svg>'
)


@dataclass(frozen=True)
class SpeakerLine:
    speaker: str | None
    html: str


def split_pages(body_html: str) -> list[str]:
    """Split a body at its `::: pagebreak` directives. A page with nothing on it is dropped."""
    pages: list[str] = [page for page in body_html.split(PAGEBREAK) if page.strip()]
    return pages or [""]


def artifact_block(puzzle_id: str, artifact: Artifact | None) -> str:
    if artifact is None:
        return f'<div class="mf-artifact mf-artifact-missing" data-artifact="{puzzle_id}"></div>'
    notes: str = "".join(
        f'<li class="mf-print-note">{SCISSORS_ICON}{html.escape(note)}</li>' for note in artifact.print_notes
    )
    notes_html: str = f'<ul class="mf-print-notes">{notes}</ul>' if notes else ""
    return (
        f'<div class="mf-artifact-block"><div class="mf-artifact" data-artifact="{puzzle_id}">{artifact.html}</div>'
        f"{notes_html}</div>"
    )


def insert_artifacts(body_html: str, artifacts: Mapping[str, Artifact | None]) -> str:
    """Replace each artifact mark (alone in its paragraph, or inside text) with the built artifact."""

    def replace(match: re.Match[str]) -> str:
        block: str = artifact_block(match.group(2), artifacts.get(match.group(2)))
        return block if match.group(1) and match.group(3) else (match.group(1) or "") + block + (match.group(3) or "")

    return ARTIFACT_MARK_PATTERN.sub(replace, body_html)


def clean_svg(svg: str) -> str:
    """Drop the XML prolog and scripts, so the SVG can sit inline in the page."""
    return SVG_NOISE_PATTERN.sub("", svg).strip()


def insert_images(body_html: str, images: Mapping[str, str]) -> str:
    """Replace each image mark with its inline SVG in a figure. The caption is already escaped HTML."""

    def replace(match: re.Match[str]) -> str:
        image_id: str = match.group(2)
        caption: str = match.group(3)
        caption_html: str = f"<figcaption>{caption}</figcaption>" if caption else ""
        figure: str = (
            f'<figure class="mf-figure" data-image="{image_id}"><div class="mf-figure-art">'
            f"{clean_svg(images.get(image_id, ''))}</div>{caption_html}</figure>"
        )
        alone: bool = bool(match.group(1) and match.group(4))
        return figure if alone else (match.group(1) or "") + figure + (match.group(4) or "")

    return IMAGE_MARK_PATTERN.sub(replace, body_html)


def speaker_lines(page_html: str) -> list[SpeakerLine]:
    """Split a page into dialogue lines ("Ana: text") and other blocks, for the chat-log and transcript kinds."""
    lines: list[SpeakerLine] = []
    position: int = 0
    for paragraph in PARAGRAPH_PATTERN.finditer(page_html):
        between: str = page_html[position : paragraph.start()].strip()
        if between:
            lines.append(SpeakerLine(speaker=None, html=between))
        position = paragraph.end()
        for line in paragraph.group(1).split("\n"):
            match: re.Match[str] | None = SPEAKER_PATTERN.match(line)
            if match is not None:
                lines.append(SpeakerLine(speaker=match.group(1).strip(), html=match.group(2)))
            else:
                lines.append(SpeakerLine(speaker=None, html=line))
    rest: str = page_html[position:].strip()
    if rest:
        lines.append(SpeakerLine(speaker=None, html=rest))
    return lines
