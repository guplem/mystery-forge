"""Read the `source/` folder of a game into models, and turn every problem into a precise finding.

The loader never raises for a problem in the game files. It loads what it can and reports the rest, so one fix loop
round can repair every broken file at once.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from mystery_forge.findings import Finding
from mystery_forge.spec.models import DocumentMeta, Flow, Puzzle, Story
from mystery_forge.yaml_loading import (
    YamlDocument,
    YamlLoadError,
    parse_yaml_text,
    read_source_text,
    split_front_matter,
)

SOURCE_FOLDER: str = "source"
NUMBERED_FILE: re.Pattern[str] = re.compile(r"^([A-Z])(\d+)")


@dataclass(frozen=True)
class SourceDocument:
    """A player document: its front matter, its Markdown body, its file, and the line where the body starts."""

    meta: DocumentMeta
    body: str
    file: str
    body_line: int


@dataclass(frozen=True)
class GameSource:
    """Everything that the agents wrote. A file that failed to load is missing here and has a finding instead."""

    root: Path
    story: Story | None
    flow: Flow | None
    puzzles: tuple[Puzzle, ...]
    documents: tuple[SourceDocument, ...]
    images: dict[str, str]


def load_game_source(game_dir: Path) -> tuple[GameSource, list[Finding]]:
    """Load `<game_dir>/source/`. Return the loaded parts and the findings for the parts that failed."""
    root: Path = game_dir / SOURCE_FOLDER
    findings: list[Finding] = []
    if not root.is_dir():
        findings.append(
            Finding(
                severity="error",
                rule="source.missing",
                message=f"The game folder has no '{SOURCE_FOLDER}' folder.",
                file=SOURCE_FOLDER,
                fix_hint="Run the setup step again, or pass the game folder (the parent of source/).",
            )
        )
        return GameSource(root, None, None, (), (), {}), findings
    story: Story | None = load_required_model(root, "story.yaml", Story, findings)
    flow: Flow | None = load_required_model(root, "flow.yaml", Flow, findings)
    puzzles: list[Puzzle] = load_puzzles(root, findings)
    documents: list[SourceDocument] = load_documents(root, findings)
    report_duplicate_ids([puzzle.id for puzzle in puzzles], "puzzle", findings)
    report_duplicate_ids([document.meta.id for document in documents], "document", findings)
    images: dict[str, str] = load_images(root, findings)
    return GameSource(root, story, flow, tuple(puzzles), tuple(documents), images), findings


def load_required_model[ModelType: BaseModel](
    root: Path, name: str, model: type[ModelType], findings: list[Finding]
) -> ModelType | None:
    path: Path = root / name
    if not path.is_file():
        findings.append(
            Finding(
                severity="error",
                rule="source.missing",
                message=f"The file {name} does not exist.",
                file=name,
                fix_hint=f"Write source/{name}. Run `forge schema {path.stem}` to see its fields.",
            )
        )
        return None
    text: str | None = read_source_file(path, name, findings)
    return load_yaml_model(text, name, model, findings) if text is not None else None


def read_source_file(path: Path, file: str, findings: list[Finding]) -> str | None:
    """Read a source file, or add a finding and return None when its bytes are not UTF-8."""
    try:
        return read_source_text(path)
    except UnicodeDecodeError as error:
        findings.append(
            Finding(
                severity="error",
                rule="source.encoding",
                message=f"The file is not UTF-8 text: byte {error.start} cannot be read.",
                file=file,
                fix_hint="Save the file as UTF-8 text.",
            )
        )
        return None


def load_yaml_model[ModelType: BaseModel](
    text: str, file: str, model: type[ModelType], findings: list[Finding], first_line: int = 1
) -> ModelType | None:
    """Parse YAML text and validate it. `first_line` shifts the lines, for front matter inside a Markdown file."""
    try:
        document: YamlDocument = parse_yaml_text(text, file)
    except YamlLoadError as error:
        line: int | None = error.line + first_line - 1 if error.line is not None else None
        findings.append(Finding(severity="error", rule="yaml.syntax", message=error.message, file=file, line=line))
        return None
    if not isinstance(document.data, dict):
        findings.append(
            Finding(
                severity="error",
                rule="schema.not_a_mapping",
                message="The file must hold a mapping of field names to values.",
                file=file,
                line=first_line,
            )
        )
        return None
    try:
        return model.model_validate(document.data)
    except ValidationError as error:
        findings.extend(validation_findings(error, document, file, first_line))
        return None


def validation_findings(error: ValidationError, document: YamlDocument, file: str, first_line: int) -> list[Finding]:
    findings: list[Finding] = []
    for issue in error.errors():
        location: tuple[str | int, ...] = tuple(issue["loc"])
        line: int | None = document.line_of(location)
        findings.append(
            Finding(
                severity="error",
                rule=f"schema.{issue['type']}",
                message=str(issue["msg"]),
                file=file,
                line=line + first_line - 1 if line is not None else first_line,
                path=".".join(str(part) for part in location),
                fix_hint=schema_fix_hint(issue),
            )
        )
    return findings


def schema_fix_hint(issue: Any) -> str:
    if issue["type"] == "extra_forbidden":
        return "Remove this field, or check its spelling against `forge schema`."
    if issue["type"] == "missing":
        return "Add this required field."
    return "Change the value so that it matches the rule in the message."


def load_puzzles(root: Path, findings: list[Finding]) -> list[Puzzle]:
    puzzles: list[Puzzle] = []
    for path in numbered_files(root / "puzzles", "*.yaml"):
        file: str = f"puzzles/{path.name}"
        text: str | None = read_source_file(path, file, findings)
        if text is None:
            continue
        puzzle: Puzzle | None = load_yaml_model(text, file, Puzzle, findings)
        if puzzle is not None and file_name_matches(path.name, puzzle.id, file, findings):
            puzzles.append(puzzle)
    return puzzles


def load_documents(root: Path, findings: list[Finding]) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for path in numbered_files(root / "documents", "*.md"):
        file: str = f"documents/{path.name}"
        text: str | None = read_source_file(path, file, findings)
        if text is None:
            continue
        try:
            header, body, body_line = split_front_matter(text)
        except YamlLoadError as error:
            findings.append(Finding(severity="error", rule="yaml.syntax", message=error.message, file=file, line=1))
            continue
        if header is None:
            findings.append(
                Finding(
                    severity="error",
                    rule="document.front_matter",
                    message="The document has no front matter.",
                    file=file,
                    line=1,
                    fix_hint="Start the file with a '---' line, the metadata fields, and another '---' line.",
                )
            )
            continue
        meta: DocumentMeta | None = load_yaml_model(header, file, DocumentMeta, findings, first_line=2)
        if meta is not None and file_name_matches(path.name, meta.id, file, findings):
            documents.append(SourceDocument(meta=meta, body=body, file=file, body_line=body_line))
    return documents


def numbered_files(folder: Path, pattern: str) -> list[Path]:
    """List the files of a folder, sorted so that P2 comes before P10."""
    if not folder.is_dir():
        return []
    return sorted(folder.glob(pattern), key=file_sort_key)


def file_sort_key(path: Path) -> tuple[str, int, str]:
    match: re.Match[str] | None = NUMBERED_FILE.match(path.name)
    if match is None:
        return ("", 0, path.name)
    return (match.group(1), int(match.group(2)), path.name)


def file_name_matches(file_name: str, model_id: str, file: str, findings: list[Finding]) -> bool:
    stem: str = file_name.rsplit(".", 1)[0]
    if stem == model_id or stem.startswith(f"{model_id}-"):
        return True
    findings.append(
        Finding(
            severity="error",
            rule="source.file_name",
            message=f"The file name '{file_name}' does not start with its id '{model_id}'.",
            file=file,
            fix_hint=f"Rename the file to '{model_id}{Path(file_name).suffix}', or fix the id inside it.",
        )
    )
    return False


def report_duplicate_ids(ids: list[str], kind: str, findings: list[Finding]) -> None:
    for duplicate_id, count in sorted(Counter(ids).items()):
        if count > 1:
            findings.append(
                Finding(
                    severity="error",
                    rule="source.duplicate_id",
                    message=f"{count} {kind} files use the id '{duplicate_id}'.",
                    fix_hint=f"Give each {kind} its own id, or delete the extra file.",
                )
            )


def load_images(root: Path, findings: list[Finding]) -> dict[str, str]:
    folder: Path = root / "images"
    if not folder.is_dir():
        return {}
    images: dict[str, str] = {}
    for path in sorted(folder.glob("*.svg")):
        text: str | None = read_source_file(path, f"images/{path.name}", findings)
        if text is not None:
            images[path.stem] = text
    return images
