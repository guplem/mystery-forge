"""Group findings by the writer that owns their files, so that each fixer subagent works on its own files only.

Fixers run in parallel. Two fixers that edit the same file lose each other's changes, so a group holds every file
that one writer owns: a puzzle with its documents, the story documents, the story, or the plan and the flow.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mystery_forge.findings import Finding, findings_to_json
from mystery_forge.spec.loader import SOURCE_FOLDER
from mystery_forge.yaml_loading import YamlLoadError, split_front_matter

STORY_GROUP: str = "story"
PLAN_GROUP: str = "plan"
DOCUMENTS_GROUP: str = "documents"
SETUP_FILES: frozenset[str] = frozenset({"config.json", "brief.json", "draw.json"})


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
    try:
        header, _, _ = split_front_matter(path.read_text(encoding="utf-8"))
    except YamlLoadError:
        return None
    if header is None:
        return None
    meta: Any = yaml.safe_load(header)
    puzzle: object = meta.get("puzzle") if isinstance(meta, dict) else None
    return str(puzzle) if puzzle else DOCUMENTS_GROUP


def plan_owners(plan_path: Path) -> dict[str, str]:
    if not plan_path.is_file():
        return {}
    try:
        plan: Any = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    owners: dict[str, str] = {}
    for puzzle in plan.get("puzzles", []) if isinstance(plan, dict) else []:
        owners[f"puzzles/{puzzle['id']}.yaml"] = puzzle["id"]
        for document in puzzle.get("documents", []):
            owners[f"documents/{document}.md"] = puzzle["id"]
    for document in plan.get("story_documents", []) if isinstance(plan, dict) else []:
        owners[f"documents/{document['id']}.md"] = DOCUMENTS_GROUP
    return owners


def group_name(file: str | None, owners: dict[str, str]) -> str | None:
    if file is None or file == "story.yaml":
        return STORY_GROUP
    if file in ("flow.yaml", "plan.yaml"):
        return PLAN_GROUP
    if file in SETUP_FILES:
        return None
    if file.startswith("images/"):
        return DOCUMENTS_GROUP
    return owners.get(file, DOCUMENTS_GROUP)


def group_files(name: str, owners: dict[str, str]) -> list[str]:
    if name == STORY_GROUP:
        return ["story.yaml"]
    if name == PLAN_GROUP:
        return ["plan.yaml", "flow.yaml"]
    owned: list[str] = [file for file, owner in owners.items() if owner == name]
    puzzle_files: list[str] = sorted(file for file in owned if file.startswith("puzzles/"))
    document_files: list[str] = sorted(file for file in owned if file.startswith("documents/"))
    extra: list[str] = ["images/"] if name == DOCUMENTS_GROUP else []
    return puzzle_files + document_files + extra


def group_findings(findings: list[Finding], game_dir: Path) -> list[FixGroup]:
    """Return one group per owner that has at least one error, with all of that owner's findings."""
    owners: dict[str, str] = file_owners(game_dir)
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        name: str | None = group_name(finding.file, owners)
        if name is not None:
            grouped.setdefault(name, []).append(finding)
    return [
        FixGroup(name=name, files=group_files(name, owners), findings=group)
        for name, group in sorted(grouped.items())
        if any(finding.severity == "error" for finding in group)
    ]


def write_fix_groups(groups: list[FixGroup], game_dir: Path, label: str) -> list[dict[str, Any]]:
    """Write `reports/fix-<label>-<group>.json` per group, and return the task items for the fixer subagents."""
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
