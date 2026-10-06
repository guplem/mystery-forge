"""The bundled fonts (`fonts/fonts.yaml`) and the `@font-face` CSS that inlines them as base64 data URLs.

Chrome blocks `@font-face` URLs on `file://` pages, so every output HTML file carries its fonts inside
(`adr/0005-rendering-stack.md`). Only the families that the chosen theme uses go in, to keep the files small.
"""

import base64
from collections.abc import Iterable
from functools import cache
from typing import Literal

from pydantic import BaseModel, ConfigDict

from mystery_forge.render.package_files import read_package_bytes, read_package_text
from mystery_forge.yaml_loading import parse_yaml_text


class FontFace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str
    weight: int
    style: Literal["normal", "italic"]


class FontFamily(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    family: str
    license: Literal["OFL-1.1", "Apache-2.0"]
    license_file: str
    source: str
    faces: list[FontFace]


class FontCatalog(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    families: list[FontFamily]


@cache
def bundled_font_families() -> dict[str, FontFamily]:
    catalog: FontCatalog = FontCatalog.model_validate(
        parse_yaml_text(read_package_text("fonts/fonts.yaml"), "fonts/fonts.yaml").data
    )
    return {family.family: family for family in catalog.families}


@cache
def face_rule(family: str, face: FontFace) -> str:
    encoded: str = base64.b64encode(read_package_bytes(f"fonts/{face.file}")).decode("ascii")
    # `font-display: block` keeps the PDF export from printing a fallback font while a face still decodes.
    return (
        f'@font-face{{font-family:"{family}";src:url(data:font/woff2;base64,{encoded}) format("woff2");'
        f"font-weight:{face.weight};font-style:{face.style};font-display:block}}"
    )


def font_face_css(families: Iterable[str]) -> str:
    """Return the `@font-face` rules of each family, in name order. An unknown family is a programming error."""
    known: dict[str, FontFamily] = bundled_font_families()
    rules: list[str] = []
    for name in sorted(set(families)):
        if name not in known:
            raise KeyError(f"No bundled font family named '{name}'.")
        rules.extend(face_rule(name, face) for face in known[name].faces)
    return "\n".join(rules)
