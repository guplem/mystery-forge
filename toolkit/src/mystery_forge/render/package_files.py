"""Read the files that ship inside the render package (templates, theme CSS, fonts) through `importlib.resources`.

The package can run from a wheel or a zip, so no code builds a file path from `__file__`.
"""

from importlib.resources import files
from importlib.resources.abc import Traversable

RENDER_PACKAGE: str = "mystery_forge.render"


def package_file(relative_path: str) -> Traversable:
    return files(RENDER_PACKAGE).joinpath(*relative_path.split("/"))


def read_package_text(relative_path: str) -> str:
    return package_file(relative_path).read_text(encoding="utf-8")


def read_package_bytes(relative_path: str) -> bytes:
    return package_file(relative_path).read_bytes()
