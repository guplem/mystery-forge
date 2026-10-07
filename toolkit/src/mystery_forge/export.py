"""Copy a rendered game to the user's output folder, in the layout that a host needs.

The top of the folder holds only what a host opens first: the manual, the materials to print, and the companion
page. The hints and the solutions sit in a folder whose name warns about spoilers. An export never overwrites an
earlier one: a second export of the same title gets " (2)".
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mystery_forge.paths import safe_folder_name, unique_folder
from mystery_forge.render.manual import COMPANION_FILE, SPOILER_FOLDER

APP_FOLDER: Final[str] = "Mystery Forge"
REQUIRED_FILES: Final[tuple[str, ...]] = ("1 - START HERE (manual).pdf", "2 - PRINT THIS (game materials).pdf")
SPOILER_FILES: Final[tuple[str, ...]] = ("3 - Hints.pdf", "4 - Solutions.pdf")


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


def export_game(render_dir: Path, root: Path, title: str) -> ExportResult:
    """Copy the outputs of `render_dir` into a new folder named after the title, inside `root`."""
    for name in (*REQUIRED_FILES, *SPOILER_FILES):
        if not (render_dir / name).is_file():
            raise ExportError(f"The render folder has no '{name}'. Run `forge render` first.")
    root.mkdir(parents=True, exist_ok=True)
    folder: Path = unique_folder(root, safe_folder_name(title))
    (folder / SPOILER_FOLDER).mkdir(parents=True)
    files: list[str] = []
    for name in REQUIRED_FILES:
        shutil.copy2(render_dir / name, folder / name)
        files.append(name)
    if (render_dir / COMPANION_FILE).is_file():
        shutil.copy2(render_dir / COMPANION_FILE, folder / COMPANION_FILE)
        files.append(COMPANION_FILE)
    for name in SPOILER_FILES:
        shutil.copy2(render_dir / name, folder / SPOILER_FOLDER / name)
        files.append(f"{SPOILER_FOLDER}/{name}")
    return ExportResult(folder=folder, files=files)
