"""SVG images that agents draw: they must be valid, safe, small, and used.

The renderer inlines each SVG into the HTML pages, so a script or an external link inside one would run or load in
the companion page and in the PDF browser. A document type declaration is refused before parsing, because entity
expansion can blow up memory.
"""

import re
from typing import Final
from xml.etree import ElementTree

from mystery_forge.findings import Finding
from mystery_forge.game import Game

MAX_IMAGE_BYTES: Final[int] = 150_000
FORBIDDEN_TAGS: Final[frozenset[str]] = frozenset({"script", "foreignobject", "iframe", "object", "embed"})
LINK_ATTRIBUTES: Final[frozenset[str]] = frozenset({"href", "src"})
IMAGE_MARK: Final[re.Pattern[str]] = re.compile(r"⟦image:([^|⟧]+)\|")


def check_images(game: Game) -> list[Finding]:
    used: set[str] = {match for document in game.documents for match in IMAGE_MARK.findall(document.body_html)}
    findings: list[Finding] = []
    for image_id, svg in sorted(game.images.items()):
        file: str = f"images/{image_id}.svg"
        problem: Finding | None = image_problem(svg, file)
        if problem is not None:
            findings.append(problem)
        elif image_id not in used:
            findings.append(
                Finding(
                    severity="warning",
                    rule="images.unused",
                    message=f"No document shows the image '{image_id}'.",
                    file=file,
                    fix_hint="Place it with {{image:<id>|caption}} in a document, or delete the file.",
                )
            )
    return findings


def image_problem(svg: str, file: str) -> Finding | None:
    if len(svg.encode()) > MAX_IMAGE_BYTES:
        return image_finding(
            "images.too_large",
            f"The image is larger than {MAX_IMAGE_BYTES // 1000} KB.",
            file,
            "Draw it with fewer, simpler shapes.",
        )
    if "<!DOCTYPE" in svg or "<!ENTITY" in svg:
        return invalid(file, "it declares a document type")
    try:
        root: ElementTree.Element = ElementTree.fromstring(svg)
    except ElementTree.ParseError as error:
        return invalid(file, str(error))
    if local_name(root.tag) != "svg":
        return invalid(file, "its root element is not <svg>")
    for element in root.iter():
        if local_name(element.tag) in FORBIDDEN_TAGS or unsafe_attribute(element):
            return image_finding(
                "images.unsafe",
                f"The image holds <{local_name(element.tag)}> content that could run code or load files.",
                file,
                "Use only plain shapes, paths, and text. No scripts, event attributes, or links outside the image.",
            )
    return None


def unsafe_attribute(element: ElementTree.Element) -> bool:
    for name, value in element.attrib.items():
        attribute: str = local_name(name).lower()
        if attribute.startswith("on"):
            return True
        if attribute in LINK_ATTRIBUTES and not value.startswith("#"):
            return True
    return False


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def invalid(file: str, reason: str) -> Finding:
    return image_finding(
        "images.invalid_svg",
        f"The image is not a valid SVG: {reason}.",
        file,
        "Write one <svg> element with a viewBox and plain shapes.",
    )


def image_finding(rule: str, message: str, file: str, fix_hint: str) -> Finding:
    return Finding(severity="error", rule=rule, message=message, file=file, fix_hint=fix_hint)
