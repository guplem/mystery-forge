"""Copy a rendered game to the user's output folder, in the layout that a host needs.

The top of the folder holds only what a host opens first: the manual, the materials to print, and the companion
page. The hints and the solutions sit in a folder whose name warns about spoilers. Every name follows the game
language. An export never overwrites an earlier one: a second export of the same title gets " (2)".
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mystery_forge.paths import safe_folder_name, unique_folder
from mystery_forge.render.sheets import OutputFileNames, OutputId

APP_FOLDER: Final[str] = "Mystery Forge"
# Every render writes these PDF files. The hints PDF and the companion page exist only when the config asks for them.
REQUIRED_OUTPUTS: Final[tuple[OutputId, ...]] = ("manual", "materials", "solutions")


class ExportError(Exception):
    """The render folder misses a file that the export needs."""


@dataclass(frozen=True)
class ExportResult:
    folder: Path
    # The exported files, relative to `folder`, with forward slashes.
    files: list[str]


def output_root(configured_folder: str, desktop: Path) -> Path:
    """The folder that receives the game folders: the config's folder, or `Desktop/Mystery Forge`."""
    return Path(configured_folder) if configured_folder else desktop / APP_FOLDER


def export_game(render_dir: Path, root: Path, title: str, names: OutputFileNames) -> ExportResult:
    """Copy the outputs of `render_dir` into a new folder named after the title, inside `root`."""
    for output in REQUIRED_OUTPUTS:
        if not (render_dir / names.pdfs[output]).is_file():
            raise ExportError(f"The render folder has no '{names.pdfs[output]}'. Run `forge render` first.")
    root.mkdir(parents=True, exist_ok=True)
    folder: Path = unique_folder(root, safe_folder_name(title))
    (folder / names.spoiler_folder).mkdir(parents=True)
    # Each pair is the name in the render folder and the path in the exported folder, in the order that a host reads.
    copies: list[tuple[str, str]] = [
        (names.pdfs["manual"], names.exported_path("manual")),
        (names.pdfs["materials"], names.exported_path("materials")),
        (names.companion, names.companion),
        (names.pdfs["hints"], names.exported_path("hints")),
        (names.pdfs["solutions"], names.exported_path("solutions")),
    ]
    files: list[str] = []
    for source, exported in copies:
        if (render_dir / source).is_file():
            shutil.copy2(render_dir / source, folder / exported)
            files.append(exported)
    return ExportResult(folder=folder, files=files)
