"""Assemble a game folder into one validated `Game`: load the source, build each puzzle, and render each document.

Assembly reports problems as findings and keeps going, so one fix round can repair everything at once. It returns no
game only when the story, the flow, the config, or the brief is missing or broken, because nothing else makes sense
without them. The semantic checks (`mystery_forge.checks`) run on the assembled game.
"""

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mystery_forge.answers import normalize_answer
from mystery_forge.brief import Brief
from mystery_forge.config import GameConfig, load_config_file
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledDocument, AssembledPuzzle, Game
from mystery_forge.mechanics.base import (
    Artifact,
    MechanicBuildError,
    MechanicContext,
    MechanicImplementation,
    parse_params,
)
from mystery_forge.mechanics.registry import all_implementations
from mystery_forge.spec.documents import (
    ARTIFACT_MARK,
    ReferenceContext,
    render_markdown,
    resolve_references,
)
from mystery_forge.spec.loader import SOURCE_FOLDER, GameSource, SourceDocument, load_game_source
from mystery_forge.spec.models import Puzzle

IMAGE_MARK_PATTERN: re.Pattern[str] = re.compile(r"⟦image:([^|⟧]+)\|([^⟧]*)⟧")


@dataclass(frozen=True)
class AssemblyResult:
    game: Game | None
    findings: list[Finding]


def assemble_game(
    game_dir: Path, implementations: Mapping[str, MechanicImplementation[Any]] | None = None
) -> AssemblyResult:
    """Load and assemble the game in `game_dir`. `implementations` replaces the mechanic registry in tests."""
    mechanics: Mapping[str, MechanicImplementation[Any]] = (
        implementations if implementations is not None else all_implementations()
    )
    source, findings = load_game_source(game_dir)
    config: GameConfig | None = load_config(game_dir, findings)
    brief: Brief | None = load_brief(game_dir, findings)
    if source.story is None or source.flow is None or config is None or brief is None:
        return AssemblyResult(game=None, findings=findings)
    documents, source_texts = assemble_documents(source, config.language, findings)
    puzzles: list[AssembledPuzzle] = assemble_puzzles(source, mechanics, config.language, source_texts, findings)
    artifacts: dict[str, Artifact] = {puzzle.source.id: puzzle.artifact for puzzle in puzzles if puzzle.artifact}
    documents = [insert_solver_texts(document, artifacts) for document in documents]
    game = Game(
        config=config,
        brief=brief,
        story=source.story,
        flow=source.flow,
        puzzles=puzzles,
        documents=documents,
        images=source.images,
        salt=game_salt(source.story.title, brief.seed),
    )
    return AssemblyResult(game=game, findings=findings)


def load_config(game_dir: Path, findings: list[Finding]) -> GameConfig | None:
    path: Path = game_dir / SOURCE_FOLDER / "config.json"
    if not path.is_file():
        findings.append(missing_file_finding("config.json"))
        return None
    result = load_config_file(path)
    for config_finding in result.findings:
        findings.append(
            Finding(
                severity="error",
                rule=config_finding.rule,
                message=config_finding.message,
                file="config.json",
                path=config_finding.path,
                fix_hint="Fix the config with the configurator page, then run the setup step again.",
            )
        )
    return result.config


def load_brief(game_dir: Path, findings: list[Finding]) -> Brief | None:
    path: Path = game_dir / SOURCE_FOLDER / "brief.json"
    if not path.is_file():
        findings.append(missing_file_finding("brief.json"))
        return None
    try:
        return Brief.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as error:
        findings.append(
            Finding(
                severity="error",
                rule="brief.invalid",
                message=f"brief.json is not valid: {error.errors()[0]['msg']}",
                file="brief.json",
                fix_hint="Do not edit brief.json by hand. Run the setup step again to write it.",
            )
        )
        return None


def missing_file_finding(name: str) -> Finding:
    return Finding(
        severity="error",
        rule="source.missing",
        message=f"The file {name} does not exist.",
        file=name,
        fix_hint="The setup step writes this file. Run it again for this game folder.",
    )


def assemble_documents(
    source: GameSource, language: str, findings: list[Finding]
) -> tuple[list[AssembledDocument], dict[str, str]]:
    """Render every document. Also return each document's text before the artifacts go in, for verifier mechanics."""
    assert source.story is not None and source.flow is not None
    context = ReferenceContext(
        language=language,
        story=source.story,
        stage_ids=frozenset(stage.id for stage in source.flow.stages),
        document_titles={document.meta.id: document.meta.title for document in source.documents},
        puzzle_ids=frozenset(puzzle.id for puzzle in source.puzzles),
        image_ids=frozenset(source.images),
    )
    documents: list[AssembledDocument] = []
    source_texts: dict[str, str] = {}
    for document in source.documents:
        assembled: AssembledDocument = assemble_document(document, context, findings)
        documents.append(assembled)
        source_texts[document.meta.id] = assembled.text
    return documents, source_texts


def assemble_document(
    document: SourceDocument, context: ReferenceContext, findings: list[Finding]
) -> AssembledDocument:
    resolved, reference_findings = resolve_references(
        document.body, document.meta.puzzle, context, document.file, document.body_line
    )
    findings.extend(reference_findings)
    rendered = render_markdown(resolved, document.file, document.body_line)
    findings.extend(rendered.findings)
    text: str = IMAGE_MARK_PATTERN.sub(lambda match: image_caption(match.group(2)), rendered.text)
    fields: dict[str, str] = {}
    for key, value in document.meta.fields.items():
        # Header fields print too (a sender, a signature), so they take the same references as the body.
        resolved_value, field_findings = resolve_references(value, document.meta.puzzle, context, document.file, 1)
        findings.extend(field_findings)
        fields[key] = resolved_value
    meta = document.meta.model_copy(update={"fields": fields})
    return AssembledDocument(meta=meta, file=document.file, body_html=rendered.html, text=text)


def image_caption(caption: str) -> str:
    return f"[Image: {caption}]" if caption else "[Image]"


def assemble_puzzles(
    source: GameSource,
    mechanics: Mapping[str, MechanicImplementation[Any]],
    language: str,
    source_texts: dict[str, str],
    findings: list[Finding],
) -> list[AssembledPuzzle]:
    codes: dict[str, str] = puzzle_codes([(puzzle.id, puzzle.stage) for puzzle in source.puzzles])
    assembled: list[AssembledPuzzle] = []
    for puzzle in source.puzzles:
        file: str = f"puzzles/{puzzle.id}.yaml"
        artifact: Artifact | None = build_artifact(puzzle, file, mechanics, language, source_texts, findings)
        answers: list[str] = [normalize_answer(text, language) for text in (puzzle.answer, *puzzle.accepted)]
        assembled.append(
            AssembledPuzzle(
                source=puzzle,
                file=file,
                code=codes[puzzle.id],
                artifact=artifact,
                accepted_normalized=list(dict.fromkeys(answers)),
            )
        )
    return assembled


def build_artifact(
    puzzle: Puzzle,
    file: str,
    mechanics: Mapping[str, MechanicImplementation[Any]],
    language: str,
    source_texts: dict[str, str],
    findings: list[Finding],
) -> Artifact | None:
    implementation: MechanicImplementation[Any] | None = mechanics.get(puzzle.mechanic)
    if implementation is None:
        findings.append(
            Finding(
                severity="error",
                rule="mechanic.unknown",
                message=f"No code builds the mechanic '{puzzle.mechanic}'.",
                file=file,
                path="mechanic",
                fix_hint="Pick an implemented mechanic: `forge catalog list --implemented`.",
            )
        )
        return None
    context = MechanicContext(
        puzzle_id=puzzle.id, answer=puzzle.answer, language=language, seed=puzzle.seed, documents=source_texts
    )
    try:
        params = parse_params(implementation, puzzle.params)
    except MechanicBuildError as error:
        findings.append(mechanic_finding("mechanic.params", error, file, "params"))
        return None
    try:
        return implementation.build(params, context)
    except MechanicBuildError as error:
        findings.append(mechanic_finding("mechanic.build", error, file, "params"))
        return None


def mechanic_finding(rule: str, error: MechanicBuildError, file: str, path: str) -> Finding:
    return Finding(severity="error", rule=rule, message=error.message, file=file, path=path, fix_hint=error.fix_hint)


def insert_solver_texts(document: AssembledDocument, artifacts: dict[str, Artifact]) -> AssembledDocument:
    text: str = document.text
    for puzzle_id, artifact in artifacts.items():
        text = text.replace(ARTIFACT_MARK.format(puzzle=puzzle_id), artifact.solver_text)
    return document.model_copy(update={"text": text})


def puzzle_codes(puzzles: list[tuple[str, str]]) -> dict[str, str]:
    """Number the puzzles inside each stage by their id number: P1 and P2 in stage A become A1 and A2."""
    codes: dict[str, str] = {}
    counters: dict[str, int] = {}
    for puzzle_id, stage in sorted(puzzles, key=lambda pair: (pair[1], int(pair[0][1:]))):
        counters[stage] = counters.get(stage, 0) + 1
        codes[puzzle_id] = f"{stage}{counters[stage]}"
    return codes


def game_salt(title: str, seed: int) -> str:
    return hashlib.sha256(f"{title}:{seed}".encode()).hexdigest()[:16]
