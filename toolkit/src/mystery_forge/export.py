"""Copy a rendered game to the user's output folder, in the layout that a host needs.

The top of the folder holds only what a host opens first: the manual, the materials to print, and the companion
page. The hints and the solutions sit in a folder whose name warns about spoilers. Every name follows the game
language. An export never overwrites an earlier one: a second export of the same title gets " (2)".

A game that the verification still blocks gets a warnings file at the top of the folder. It names, in the game language
and in plain words, each puzzle and the accusation form that may have problems. It reveals no answer.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mystery_forge.i18n import text
from mystery_forge.paths import safe_folder_name, unique_folder
from mystery_forge.render.sheets import OutputFileNames, OutputId
from mystery_forge.verification import DEDUCTION_KEY, ExportProblem

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


def warnings_text(problems: list[ExportProblem], language: str) -> str:
    """The warnings file for these problems, in the language, or "" when there is no problem."""
    if not problems:
        return ""
    by_code: dict[str, list[str]] = {}
    for problem in problems:
        by_code.setdefault(problem.code, []).append(text(language, f"export_warning_{problem.kind}"))
    lines: list[str] = []
    for code, sentences in by_code.items():
        # Each text starts in lower case after the colon, so the second and later sentences start with a capital.
        joined: str = " ".join([sentences[0], *(sentence[:1].upper() + sentence[1:] for sentence in sentences[1:])])
        if code == DEDUCTION_KEY:
            lines.append(f"- {text(language, 'export_warning_accusation', problems=joined)}")
        else:
            lines.append(f"- {text(language, 'export_warning_puzzle', code=code, problems=joined)}")
    paragraphs: list[str] = [
        text(language, "export_warnings_title"),
        text(language, "export_warnings_intro"),
        "\n".join(lines),
        text(language, "export_warnings_fix"),
    ]
    return "\n\n".join(paragraphs) + "\n"


def export_game(render_dir: Path, root: Path, title: str, names: OutputFileNames, warnings: str = "") -> ExportResult:
    """Copy the outputs of `render_dir` into a new folder named after the title, inside `root`.

    Non-empty `warnings` go first, into the warnings file.
    """
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
    if warnings:
        # The byte order mark makes older Windows and macOS text editors read the file as UTF-8.
        (folder / names.warnings).write_text(warnings, encoding="utf-8-sig", newline="\n")
        files.append(names.warnings)
    for source, exported in copies:
        if (render_dir / source).is_file():
            shutil.copy2(render_dir / source, folder / exported)
            files.append(exported)
    return ExportResult(folder=folder, files=files)
