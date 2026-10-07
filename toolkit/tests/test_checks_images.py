import pytest
from test_checks_support import golden_game, rules

from mystery_forge.checks.images import MAX_IMAGE_BYTES, check_images
from mystery_forge.game import Game

SAFE_SVG: str = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>A round lamp</title>'
    '<circle cx="5" cy="5" r="4" fill="currentColor"/></svg>'
)
UNTITLED_SVG: str = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="5" cy="5" r="4"/></svg>'


def with_images(images: dict[str, str], referenced: tuple[str, ...] = ("lamp",), document: int = 0) -> Game:
    game = golden_game()
    first = game.documents[document]
    marks = "".join(f"<p>⟦image:{image}|A caption⟧</p>" for image in referenced)
    documents = list(game.documents)
    documents[document] = first.model_copy(update={"body_html": first.body_html + marks})
    return game.model_copy(update={"images": images, "documents": documents})


def test_a_safe_referenced_svg_passes() -> None:
    assert check_images(with_images({"lamp": SAFE_SVG})) == []


def test_the_golden_game_has_no_images_and_no_findings() -> None:
    assert check_images(golden_game()) == []


@pytest.mark.parametrize(
    "svg",
    [
        "<svg><script>alert(1)</script></svg>",
        '<svg onload="alert(1)"><rect/></svg>',
        '<svg><a href="javascript:alert(1)"><rect/></a></svg>',
        '<svg><image href="https://example.com/x.png"/></svg>',
        '<svg xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="http://example.com/a.svg#b"/></svg>',
        "<svg><foreignObject><div>x</div></foreignObject></svg>",
    ],
)
def test_unsafe_svg_content_is_an_error(svg: str) -> None:
    assert rules(check_images(with_images({"lamp": svg}))) == ["images.unsafe"]


@pytest.mark.parametrize(
    "svg", ["<svg><circle></svg>", "<div>not svg</div>", "", "<?xml?><!DOCTYPE x [<!ENTITY a 'b'>]><svg/>"]
)
def test_broken_or_non_svg_files_are_errors(svg: str) -> None:
    assert rules(check_images(with_images({"lamp": svg}))) == ["images.invalid_svg"]


def test_a_huge_image_is_an_error() -> None:
    padding = "<!--" + "x" * MAX_IMAGE_BYTES + "-->"
    huge = SAFE_SVG.replace("</svg>", padding + "</svg>")
    assert rules(check_images(with_images({"lamp": huge}))) == ["images.too_large"]


def test_an_unused_image_is_a_warning() -> None:
    findings = check_images(with_images({"lamp": SAFE_SVG}, referenced=()))
    assert rules(findings) == ["images.unused"]
    assert findings[0].severity == "warning"
    assert findings[0].file == "images/lamp.svg"


def test_local_fragment_links_are_fine() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<title>Two lines</title><defs><path id="p" d="M0 0L1 1"/></defs><use xlink:href="#p"/><use href="#p"/></svg>'
    )
    assert check_images(with_images({"lamp": svg})) == []


def test_an_image_without_a_title_is_a_warning_and_an_error_in_puzzle_material() -> None:
    """Live game 6: the solver panel saw a rebus as "[Image]", so it could not test the puzzle."""
    story_document = check_images(with_images({"lamp": UNTITLED_SVG}))
    assert [(finding.rule, finding.severity) for finding in story_document] == [("images.no_title", "warning")]
    puzzle_document = check_images(with_images({"lamp": UNTITLED_SVG}, document=1))
    assert [(finding.rule, finding.severity) for finding in puzzle_document] == [("images.no_title", "error")]
    assert puzzle_document[0].file == "images/lamp.svg"
