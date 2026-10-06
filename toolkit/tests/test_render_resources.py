import base64

import pytest

from mystery_forge.render.fonts import bundled_font_families, font_face_css
from mystery_forge.render.package_files import read_package_bytes, read_package_text


def test_package_files_load_through_importlib_resources() -> None:
    assert "families:" in read_package_text("fonts/fonts.yaml")
    assert read_package_bytes("fonts/Caveat-400.woff2")[:4] == b"wOF2"


def test_every_bundled_face_exists_and_keeps_its_license() -> None:
    families = bundled_font_families()
    assert "Atkinson Hyperlegible" in families
    total_bytes: int = 0
    for family in families.values():
        assert family.license in ("OFL-1.1", "Apache-2.0")
        assert read_package_text(f"fonts/{family.license_file}").strip()
        for face in family.faces:
            total_bytes += len(read_package_bytes(f"fonts/{face.file}"))
    assert total_bytes < 2_500_000


def test_font_face_css_inlines_each_face_of_the_families_once() -> None:
    css: str = font_face_css(["Caveat", "Bebas Neue", "Caveat"])
    assert css.count("@font-face") == 3
    assert 'font-family:"Caveat"' in css
    assert "font-weight:700" in css
    encoded: str = css.split("base64,")[1].split(")")[0]
    assert base64.b64decode(encoded)[:4] == b"wOF2"
    assert css.index("Bebas Neue") < css.index("Caveat")


def test_font_face_css_rejects_an_unknown_family() -> None:
    with pytest.raises(KeyError, match="Comic"):
        font_face_css(["Comic"])
