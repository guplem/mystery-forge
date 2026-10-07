"""Group findings by the writer that owns their files, so that each fixer subagent works on its own files only.

Fixers run in parallel. Two fixers that edit the same file lose each other's changes, so a group holds every file
that one writer owns: a puzzle with its documents, the story documents, the story, or the plan and the flow. A
finding with no file (the budget, the variety) needs the "game" group, which holds the plan, the flow, and every
puzzle, so it runs alone in its round.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mystery_forge.findings import Finding, findings_to_json
from mystery_forge.spec.loader import SOURCE_FOLDER
from mystery_forge.yaml_loading import YamlLoadError, parse_yaml_text, read_source_text, split_front_matter

STORY_GROUP: str = "story"
PLAN_GROUP: str = "plan"
DOCUMENTS_GROUP: str = "documents"
GAME_GROUP: str = "game"
SETUP_FILES: frozenset[str] = frozenset({"config.json", "brief.json", "draw.json"})
TOOLKIT_RULES: frozenset[str] = frozenset({"render.toolkit_overflow"})


@dataclass(frozen=True)
class FixGroup:
    name: str
    files: list[str]
    findings: list[Finding]


def file_owners(game_dir: Path) -> dict[str, str]:
    """Map each source file (relative to source/) to its owner: a puzzle id, or the story documents."""
    root: Path = game_dir / SOURCE_FOLDER
    owners: dict[str, str] = {}
    for path in sorted((root / "puzzles").glob("*.yaml")):
        owners[f"puzzles/{path.name}"] = path.stem.split("-")[0]
    for path in sorted((root / "documents").glob("*.md")):
        owner: str | None = document_owner(path)
        if owner is not None:
            owners[f"documents/{path.name}"] = owner
    owners.update(plan_owners(root / "plan.yaml"))
    return owners


def document_owner(path: Path) -> str | None:
    """Return the owner that the front matter names, or None when the file cannot tell (the loader reports why)."""
    try:
        header, _, _ = split_front_matter(read_source_text(path))
        meta: Any = parse_yaml_text(header, path.name).data if header is not None else None
    except (YamlLoadError, UnicodeDecodeError):
        return None
    if not isinstance(meta, dict):
        return None
    puzzle: object = meta.get("puzzle")
    return str(puzzle) if puzzle else DOCUMENTS_GROUP


def plan_owners(plan_path: Path) -> dict[str, str]:
    """Map the files that the plan assigns to their owners. Skip a malformed entry: the plan check reports it."""
    if not plan_path.is_file():
        return {}
    try:
        plan: Any = parse_yaml_text(read_source_text(plan_path), plan_path.name).data
    except (YamlLoadError, UnicodeDecodeError):
        return {}
    if not isinstance(plan, dict):
        return {}
    owners: dict[str, str] = {}
    for puzzle_id, puzzle in plan_entries(plan.get("puzzles")):
        owners[f"puzzles/{puzzle_id}.yaml"] = puzzle_id
        for document in plan_list(puzzle.get("documents")):
            if isinstance(document, str):
                owners[f"documents/{document}.md"] = puzzle_id
    for document_id, _ in plan_entries(plan.get("story_documents")):
        owners[f"documents/{document_id}.md"] = DOCUMENTS_GROUP
    return owners


def plan_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def plan_entries(value: object) -> list[tuple[str, dict[str, Any]]]:
    """Return the plan entries that are mappings with a text `id`, as (id, entry) pairs."""
    return [
        (entry["id"], entry)
        for entry in plan_list(value)
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    ]


def group_name(file: str | None, owners: dict[str, str]) -> str | None:
    if file is None:
        return GAME_GROUP
    if file == "story.yaml":
        return STORY_GROUP
    if file in ("flow.yaml", "plan.yaml"):
        return PLAN_GROUP
    # Setup files and the toolkit's own pages (materials.html, solutions.html) are not game sources that a writer owns.
    if file in SETUP_FILES or file.endswith(".html"):
        return None
    if file.startswith("images/"):
        return DOCUMENTS_GROUP
    return owners.get(file, DOCUMENTS_GROUP)


def group_files(name: str, owners: dict[str, str]) -> list[str]:
    if name == STORY_GROUP:
        return ["story.yaml"]
    if name == PLAN_GROUP:
        return ["plan.yaml", "flow.yaml"]
    if name == GAME_GROUP:
        return ["plan.yaml", "flow.yaml", *sorted(file for file in owners if file.startswith("puzzles/"))]
    owned: list[str] = [file for file, owner in owners.items() if owner == name]
    puzzle_files: list[str] = sorted(file for file in owned if file.startswith("puzzles/"))
    document_files: list[str] = sorted(file for file in owned if file.startswith("documents/"))
    extra: list[str] = ["images/"] if name == DOCUMENTS_GROUP else []
    return puzzle_files + document_files + extra


def group_findings(findings: list[Finding], game_dir: Path) -> list[FixGroup]:
    """Return one group per owner that has at least one error, with all of that owner's findings.

    The "game" group shares files with every puzzle group and the plan group, so when it exists it is the only group:
    the other groups come back in the next round.
    """
    owners: dict[str, str] = file_owners(game_dir)
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        # A toolkit bug has no game file: no writer can fix it, so it goes to no fixer.
        name: str | None = None if finding.rule in TOOLKIT_RULES else group_name(finding.file, owners)
        if name is not None:
            grouped.setdefault(name, []).append(finding)
    groups: list[FixGroup] = [
        FixGroup(name=name, files=group_files(name, owners), findings=group)
        for name, group in sorted(grouped.items())
        if any(finding.severity == "error" for finding in group)
    ]
    game_groups: list[FixGroup] = [group for group in groups if group.name == GAME_GROUP]
    return game_groups or groups


def write_fix_groups(groups: list[FixGroup], game_dir: Path, label: str, write: bool = True) -> list[dict[str, Any]]:
    """Write `reports/fix-<label>-<group>.json` per group, and return the task items for the fixer subagents.

    With `write` False, write nothing and return the items without their `findings_file`.
    """
    if not write:
        return [{"name": group.name, "files": group.files} for group in groups]
    reports: Path = game_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for group in groups:
        path: Path = reports / f"fix-{label}-{group.name}.json"
        path.write_text(
            json.dumps({"group": group.name, "files": group.files, "findings": findings_to_json(group.findings)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )  # fmt: skip
        entries.append({"name": group.name, "files": group.files, "findings_file": str(path)})
    return entries
