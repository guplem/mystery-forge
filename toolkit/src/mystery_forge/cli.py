"""The `forge` command line. Agents and pskill script blocks call it from `generator/`.

Every verb prints ONE JSON object and exits 0 when it ran, also when it found problems (`"ok": false`), and 2 on a
usage or environment error. A crash inside a verb also prints one JSON object and exits 2. pskill pauses a run
on a non-zero exit and cuts stdout at 64 KiB, so the output stays small: at most `MAX_FINDINGS_IN_OUTPUT` findings,
and the full report goes to a file under `<game>/reports/`.
"""

import argparse
import json
import os
import secrets
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, TextIO

import yaml
from pydantic import BaseModel

from mystery_forge import cli_game
from mystery_forge.assemble import AssemblyResult, assemble_game, load_brief, load_config
from mystery_forge.brief import Brief, derive_brief
from mystery_forge.catalog.loader import design_rules_text, load_mechanics, mechanic_by_id
from mystery_forge.catalog.models import Mechanic
from mystery_forge.cli_output import BROWSER_FIX, OutputOptions, capped_findings, emit, optional_report, parse_file_list
from mystery_forge.config import ConfigLoadResult, GameConfig, load_config_file, normalize_config
from mystery_forge.draw import Draw, draw_ingredients
from mystery_forge.findings import Finding, count_errors
from mystery_forge.mechanics.base import MechanicImplementation
from mystery_forge.mechanics.registry import all_implementations
from mystery_forge.paths import (
    KnownFolderReader,
    SystemFolders,
    newest_config_file,
    read_windows_known_folder,
    slugify,
    system_folders,
)
from mystery_forge.render.pdf import BrowserNotFoundError, launch_first_available
from mystery_forge.spec.documents import ALL_DIRECTIVES
from mystery_forge.spec.loader import SOURCE_FOLDER
from mystery_forge.spec.models import DocumentMeta, Flow, Puzzle, Story

type VerbHandler = Callable[[argparse.Namespace, TextIO], int]

RECENT_GAMES_TO_AVOID: int = 5
PANEL_FLAG_HELP: str = "false (or False, 0) when the run skipped the solver panel."
MAX_SEED: int = 2_147_483_647
SCHEMAS: dict[str, type[BaseModel]] = {"story": Story, "flow": Flow, "puzzle": Puzzle, "document": DocumentMeta}
REFERENCE_FORMS: dict[str, str] = {
    "{{char:<id>}}": "The character's name. Also .role, .age, .description.",
    "{{place:<id>}}": "The location's name.",
    "{{object:<id>}}": "The object's name.",
    "{{event:<id>.date}}": "The event's start date in the game language. Also .time (HH:MM) and .weekday.",
    "{{doc:<document id>}}": "The title of another document.",
    "{{stage:<stage id>}}": "The envelope label, such as 'Envelope B' in the game language.",
    "{{artifact}}": "The built material of the puzzle named in the front matter. Or {{artifact:<puzzle id>}}.",
    "{{artifact:<puzzle id>.<part>}}": "One part of a built material, such as key1 of a key that key_parts splits.",
    "{{image:<id>}}": "The SVG image images/<id>.svg. Add a caption with {{image:<id>|caption}}.",
}


def find_system_folders() -> SystemFolders:
    reader: KnownFolderReader = read_windows_known_folder if sys.platform == "win32" else (lambda name: None)
    return system_folders(sys.platform, Path.home(), os.environ, reader)


def random_seed() -> int:
    return secrets.randbelow(MAX_SEED) + 1


def probe_browser() -> str | None:  # pragma: no cover - launches a real browser; the browser tests cover rendering
    """Return the name of the first browser that Playwright can start, or None."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        try:
            browser, channel = launch_first_available(
                lambda channel: (playwright.chromium.launch(channel=channel), channel)
            )
        except BrowserNotFoundError:
            return None
        browser.close()
        return channel or "chromium"


def write_json(path: Path, model: BaseModel) -> None:
    path.write_text(json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_setup(arguments: argparse.Namespace, output: TextIO) -> int:
    if arguments.game:
        return setup_existing_game(Path(arguments.game), output)
    folders: SystemFolders = find_system_folders()
    config_path: Path | None = None
    # The generator passes the user's answer as --config; the word "defaults" asks for the default config.
    use_defaults: bool = arguments.defaults or arguments.config == "defaults"
    if arguments.config and not use_defaults:
        config_path = Path(arguments.config)
        if not config_path.is_file():
            emit(output, {"ok": False, "message": f"The config file {config_path} does not exist."})
            return 2
    elif not use_defaults:
        config_path = newest_config_file(folders.downloads)
        if config_path is None:
            emit(output, {"ok": False, "findings": [not_found_finding(folders.downloads)]})
            return 0
    result: ConfigLoadResult = load_config_file(config_path) if config_path else normalize_config({"schema_version": 1})
    if result.config is None:
        findings: list[dict[str, Any]] = [finding.model_dump() for finding in result.findings]
        emit(output, {"ok": False, "config_file": str(config_path), "findings": findings})
        return 0
    config: GameConfig = result.config
    games_dir: Path = Path(arguments.games_dir)
    brief: Brief = derive_brief(config, config.generation.seed or random_seed())
    implemented: frozenset[str] = frozenset(all_implementations())
    draw: Draw = draw_ingredients(config, brief, implemented, avoid_settings=recent_settings(games_dir))
    game_dir: Path = new_game_folder(games_dir, config)
    source: Path = game_dir / "source"
    source.mkdir(parents=True)
    write_json(source / "config.json", config)
    write_json(source / "brief.json", brief)
    write_json(source / "draw.json", draw)
    emit(
        output,
        {
            "ok": True,
            "game_dir": str(game_dir),
            "config_file": str(config_path) if config_path else None,
            "summary": config_summary(config),
            "brief": brief.model_dump(mode="json"),
            "draw_file": str(source / "draw.json"),
        },
    )
    return 0


def setup_existing_game(game_dir: Path, output: TextIO) -> int:
    """Load a game folder that exists, so that a run can change it. Nothing is drawn or written."""
    findings: list[Finding] = []
    config: GameConfig | None = load_config(game_dir, findings)
    brief: Brief | None = load_brief(game_dir, findings)
    if config is None or brief is None:
        emit(output, {"ok": False, **capped_findings(findings)})
        return 0
    emit(
        output,
        {
            "ok": True,
            "game_dir": str(game_dir),
            "config_file": None,
            "summary": config_summary(config),
            "brief": brief.model_dump(mode="json"),
            "draw_file": str(game_dir / SOURCE_FOLDER / "draw.json"),
        },
    )
    return 0


# The config fields that a finished game can change: how it prints and what the host adds. A dotted prefix ending in
# "." allows every field of that section. Any other change (players, length, language, audience) needs a new game.
CHANGEABLE_CONFIG_FIELDS: tuple[str, ...] = (
    "equipment.",
    "visuals.",
    "assistance.",
    "output.",
    "personalization.host_name",
    "personalization.dedication",
    "players.names",
)


def changeable(field: str) -> bool:
    return any(
        field.startswith(prefix) if prefix.endswith(".") else field == prefix for prefix in CHANGEABLE_CONFIG_FIELDS
    )


def command_config(arguments: argparse.Namespace, output: TextIO) -> int:
    """Change print settings of a game's config.json, check the result against the schema, and write it."""
    path: Path = Path(arguments.game) / SOURCE_FOLDER / "config.json"
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for assignment in arguments.set:
        field, separator, value = assignment.partition("=")
        section, _, key = field.partition(".")
        if not separator or not changeable(field) or key not in raw.get(section, {}):
            allowed: str = ", ".join(CHANGEABLE_CONFIG_FIELDS)
            message: str = (
                f"'{assignment}' is not a change that a finished game can take. Use <field>=<value> with a field of: "
                f"{allowed}. Other changes need a new game."
            )
            emit(output, {"ok": False, "message": message})
            return 0
        raw[section][key] = config_value(value)
    result: ConfigLoadResult = normalize_config(raw)
    if result.config is None:
        emit(output, {"ok": False, "findings": [finding.model_dump() for finding in result.findings]})
        return 0
    write_json(path, result.config)
    emit(output, {"ok": True, "summary": config_summary(result.config)})
    return 0


def config_value(value: str) -> Any:
    """A JSON value (false, 3, ["Ana"]), or the text itself (black_and_white)."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def command_games(arguments: argparse.Namespace, output: TextIO) -> int:
    """List the game folders, newest first, with their titles, so an agent finds the game that a user names."""
    games_dir: Path = Path(arguments.games_dir)
    folders: list[Path] = sorted(games_dir.iterdir(), reverse=True) if games_dir.is_dir() else []
    games: list[dict[str, Any]] = [
        {"game_dir": str(folder), "title": story_title(folder), "rendered": (folder / "render").is_dir()}
        for folder in folders
        if (folder / SOURCE_FOLDER / "config.json").is_file()
    ]
    emit(output, {"ok": True, "games": games})
    return 0


def story_title(game_dir: Path) -> str:
    """The title in story.yaml, or "" when the story is missing or does not load."""
    try:
        loaded: Any = yaml.safe_load((game_dir / SOURCE_FOLDER / "story.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return ""
    return str(loaded.get("title", "")) if isinstance(loaded, dict) else ""


def not_found_finding(downloads: Path) -> dict[str, Any]:
    return {
        "severity": "error",
        "rule": "config.not_found",
        "message": f"No *.mystery-config.json file in {downloads}.",
        "fix_hint": "Ask the user for the config file path, or use --defaults.",
    }


def config_summary(config: GameConfig) -> dict[str, Any]:
    return {
        "players": config.players.count,
        "duration_minutes": config.duration_minutes,
        "difficulty": config.difficulty,
        "language": config.language,
        "audience": config.audience,
        "format": config.format,
        "idea": config.theme.idea,
        "quality": config.generation.quality,
        "pick_concept": config.generation.pick_concept,
        "host": config.host,
        "images": config.visuals.images,
    }


def recent_settings(games_dir: Path) -> frozenset[str]:
    if not games_dir.is_dir():
        return frozenset()
    draws: list[Path] = sorted(games_dir.glob("*/source/draw.json"), key=lambda path: path.stat().st_mtime)
    settings: set[str] = set()
    for path in draws[-RECENT_GAMES_TO_AVOID:]:
        try:
            settings.update(str(item["id"]) for item in json.loads(path.read_text(encoding="utf-8"))["settings"])
        except (ValueError, KeyError, TypeError):
            continue  # A setup that crashed can leave a broken draw. It holds no setting to avoid.
    return frozenset(settings)


def new_game_folder(games_dir: Path, config: GameConfig) -> Path:
    idea_words: str = " ".join(config.theme.idea.split()[:6])
    base: str = f"{date.today().isoformat()}-{slugify(idea_words)}"
    candidate: Path = games_dir / base
    number: int = 2
    while candidate.exists():
        candidate = games_dir / f"{base}-{number}"
        number += 1
    return candidate


def command_assemble(arguments: argparse.Namespace, output: TextIO) -> int:
    game_dir: Path = Path(arguments.game)
    options: OutputOptions = cli_game.output_options(arguments)
    result: AssemblyResult = assemble_game(game_dir)
    written: bool = False
    if result.game is not None and options.write:
        (game_dir / "game.json").write_text(result.game.model_dump_json(indent=2), encoding="utf-8")
        written = True
    findings: list[Finding] = options.selected(result.findings)
    emit(
        output,
        {
            "ok": result.game is not None and count_errors(findings) == 0,
            "game_written": written,
            "report": optional_report(game_dir, "assemble", findings, options),
            **capped_findings(findings),
        },
    )
    return 0


def command_catalog(arguments: argparse.Namespace, output: TextIO) -> int:
    implemented: set[str] = set(all_implementations())
    if arguments.catalog_command == "rules":
        output.write(design_rules_text())
        return 0
    if arguments.catalog_command == "list":
        mechanics: list[dict[str, Any]] = [
            {
                "id": mechanic.id,
                "name": mechanic.name,
                "category": mechanic.category,
                "player_action": mechanic.player_action,
                "verification": mechanic.verification,
                "implemented": mechanic.id in implemented,
                "summary": mechanic.summary,
            }
            for mechanic in load_mechanics()
            if not arguments.implemented or mechanic.id in implemented
        ]
        emit(output, {"ok": True, "mechanics": mechanics})
        return 0
    try:
        mechanic: Mechanic = mechanic_by_id(arguments.mechanic_id)
    except KeyError as error:
        emit(output, {"ok": False, "message": str(error.args[0])})
        return 2
    implementation: MechanicImplementation[Any] | None = all_implementations().get(mechanic.id)
    emit(
        output,
        {
            "ok": True,
            "mechanic": mechanic.model_dump(mode="json"),
            "implemented": implementation is not None,
            "params_schema": implementation.params_model.model_json_schema() if implementation else None,
        },
    )
    return 0


def command_schema(arguments: argparse.Namespace, output: TextIO) -> int:
    if arguments.name == "references":
        emit(output, {"references": REFERENCE_FORMS, "directives": sorted(ALL_DIRECTIVES)})
        return 0
    emit(output, SCHEMAS[arguments.name].model_json_schema())
    return 0


def command_doctor(arguments: argparse.Namespace, output: TextIO) -> int:
    folders: SystemFolders = find_system_folders()
    browser: str | None = probe_browser()
    payload: dict[str, Any] = {
        "ok": browser is not None,
        "python": sys.version.split()[0],
        "browser": browser,
        "desktop": str(folders.desktop),
        "downloads": str(folders.downloads),
    }
    if browser is None:
        payload["fix"] = BROWSER_FIX
    emit(output, payload)
    return 0


def command_export(arguments: argparse.Namespace, output: TextIO) -> int:
    return cli_game.command_export(arguments, output, find_system_folders())


def add_output_flags(parser: argparse.ArgumentParser) -> None:
    """Add the flags that let parallel fixers run a verb without overwriting the shared reports."""
    parser.add_argument(
        "--only",
        type=parse_file_list,
        help="Report only the findings of these source files, separated by commas, relative to source/.",
    )
    parser.add_argument(
        "--no-write", action="store_true", help="Print only: write no report, game.json, ledger, or fix file."
    )


def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="forge", description="Build, check, and render Mystery Forge games."
    )
    verbs: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(dest="verb", required=True)
    setup = verbs.add_parser("setup", help="Create a game folder from a config file.")
    setup.add_argument("--config", help="The config file. Default: the newest *.mystery-config.json in Downloads.")
    setup.add_argument("--defaults", action="store_true", help="Use the default config, with no file.")
    setup.add_argument("--games-dir", default="games", help="The folder that holds the game folders.")
    setup.add_argument("--game", default="", help="Load this existing game folder instead, to change it.")
    setup.set_defaults(handler=command_setup)
    config = verbs.add_parser("config", help="Change the print settings of an existing game.")
    config.add_argument("--game", required=True, help="The game folder.")
    config.add_argument(
        "--set", action="append", required=True, help="<field>=<value>, such as equipment.printer=black_and_white."
    )
    config.set_defaults(handler=command_config)
    games = verbs.add_parser("games", help="List the game folders, newest first, with their titles.")
    games.add_argument("--games-dir", default="games", help="The folder that holds the game folders.")
    games.set_defaults(handler=command_games)
    assemble = verbs.add_parser("assemble", help="Load, build, and assemble a game into game.json.")
    assemble.add_argument("--game", required=True, help="The game folder (the parent of source/).")
    add_output_flags(assemble)
    assemble.set_defaults(handler=command_assemble)
    catalog = verbs.add_parser("catalog", help="Read the mechanic catalog.")
    catalog_verbs = catalog.add_subparsers(dest="catalog_command", required=True)
    listing = catalog_verbs.add_parser("list", help="List the mechanics.")
    listing.add_argument("--implemented", action="store_true", help="Only mechanics that the toolkit can use.")
    show = catalog_verbs.add_parser("show", help="Show one mechanic and its params.")
    show.add_argument("mechanic_id")
    catalog_verbs.add_parser("rules", help="Print the design rules for game writers.")
    catalog.set_defaults(handler=command_catalog)
    schema = verbs.add_parser("schema", help="Print the JSON schema of a source file, or the reference forms.")
    schema.add_argument("name", choices=[*SCHEMAS, "references"])
    schema.set_defaults(handler=command_schema)
    doctor = verbs.add_parser("doctor", help="Check the browser and the folders.")
    doctor.set_defaults(handler=command_doctor)
    check = verbs.add_parser("check", help="Check the story, the plan, or the full game, and group the findings.")
    check.add_argument("--game", required=True, help="The game folder (the parent of source/).")
    check.add_argument("--scope", choices=["story", "plan", "full"], default="full", help="What to check.")
    add_output_flags(check)
    check.set_defaults(handler=cli_game.command_check)
    writer_tasks = verbs.add_parser("writer-tasks", help="List one writing task per planned puzzle.")
    writer_tasks.add_argument("--game", required=True, help="The game folder.")
    writer_tasks.set_defaults(handler=cli_game.command_writer_tasks)
    material = verbs.add_parser("material", help="Print the built material of one puzzle as text.")
    material.add_argument("--game", required=True, help="The game folder.")
    material.add_argument("--puzzle", required=True, help="The puzzle id, such as P1.")
    material.set_defaults(handler=cli_game.command_material)
    strings = verbs.add_parser(
        "strings",
        help="Write the fixed-text template for a language without a checked table, and check its translation.",
    )
    strings.add_argument("--game", required=True, help="The game folder.")
    strings.set_defaults(handler=cli_game.command_strings)
    packets = verbs.add_parser(
        "packets", help="Write the solver packets of each stage, the story-only packet, and the guesser packet."
    )
    packets.add_argument("--game", required=True, help="The game folder.")
    packets.add_argument(
        "--all", action="store_true", help="Write a solver task for every stage, also the stages that already passed."
    )
    packets.set_defaults(handler=cli_game.command_packets)
    judge = verbs.add_parser("judge", help="Judge the solver answers (JSON on stdin) against the official answers.")
    judge.add_argument("--game", required=True, help="The game folder.")
    judge.add_argument("--input", help="The JSON input as text, instead of stdin.")
    judge.set_defaults(handler=cli_game.command_judge)
    status = verbs.add_parser("status", help="List the verifications that are older than the files they checked.")
    status.add_argument("--game", required=True, help="The game folder.")
    status.add_argument("--panel", default="true", help=PANEL_FLAG_HELP)
    status.set_defaults(handler=cli_game.command_status)
    render = verbs.add_parser("render", help="Render the HTML pages, the PDFs, and the previews, and check them.")
    render.add_argument("--game", required=True, help="The game folder.")
    render.add_argument("--html-only", action="store_true", help="Write the HTML pages only, with no browser.")
    add_output_flags(render)
    render.set_defaults(handler=cli_game.command_render)
    export = verbs.add_parser("export", help="Copy the rendered game to the output folder.")
    export.add_argument("--game", required=True, help="The game folder.")
    export.add_argument("--to", help="The folder that receives the game folder. Default: the config's, or Desktop.")
    export.add_argument("--panel", default="true", help=PANEL_FLAG_HELP)
    export.add_argument("--force", action="store_true", help="Export even when the verification blocks the game.")
    export.set_defaults(handler=command_export)
    return parser


def main(argv: list[str] | None = None, output: TextIO | None = None) -> int:
    stream: TextIO = output if output is not None else sys.stdout
    if stream is sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # The judge reads JSON on stdin, and the Windows default (cp1252) breaks accented text.
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    arguments: argparse.Namespace = build_parser().parse_args(argv)
    handler: VerbHandler = arguments.handler
    game: str | None = getattr(arguments, "game", None)
    # A mistyped game path must not become a new folder full of reports for a game that does not exist.
    if game and not (Path(game) / SOURCE_FOLDER).is_dir():
        emit(stream, {"ok": False, "message": f"The game folder {game} has no source folder. Check the path."})
        return 2
    try:
        exit_code: int = handler(arguments, stream)
    except Exception as error:
        # The boundary of every verb: a crash prints one JSON object, and the non-zero exit pauses the pskill run.
        emit(stream, {"ok": False, "message": f"{type(error).__name__}: {error}"})
        return 2
    return exit_code
