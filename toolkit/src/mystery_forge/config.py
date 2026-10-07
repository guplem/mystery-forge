"""Game config loading: validation against the shared schema, defaults, and the typed model.

`contracts/game-config.schema.json` is the one definition of a valid config. The JavaScript configurator validates
the same file with its own small validator, and `contracts/config-vectors.json` keeps both sides equal. The schema
holds every default value, so the pydantic models below declare no defaults of their own.
"""

import copy
import json
from functools import cache
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator, ValidationError
from pydantic import BaseModel, ConfigDict

CONFIG_SCHEMA_PATH: Path = Path(__file__).resolve().parents[3] / "contracts" / "game-config.schema.json"

Audience = Literal["kids", "family", "teens", "adults", "puzzle_fans"]
GameFormat = Literal["envelopes", "case_file", "both"]
HostRole = Literal["self_running", "host_plays", "game_master"]
Difficulty = Literal["easy", "medium", "hard", "expert"]
Language = Literal[
    "en",
    "es",
    "ca",
    "fr",
    "de",
    "it",
    "pt",
    "af",
    "ar",
    "bg",
    "bn",
    "cs",
    "cy",
    "da",
    "el",
    "et",
    "eu",
    "fa",
    "fi",
    "ga",
    "gl",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "is",
    "ja",
    "ko",
    "lt",
    "lv",
    "ms",
    "nb",
    "nl",
    "pl",
    "ro",
    "ru",
    "sk",
    "sl",
    "sr",
    "sv",
    "sw",
    "ta",
    "th",
    "tl",
    "tr",
    "uk",
    "ur",
    "vi",
    "zh",
]
Tone = Literal["surprise", "cozy", "adventure", "noir", "spooky", "comedic", "dramatic"]
Era = Literal["any", "historical", "modern", "future", "fantasy"]
ScaryLevel = Literal["none", "mild", "spooky"]
ReadingLoad = Literal["light", "medium", "heavy"]
PuzzlePreference = Literal["like", "neutral", "avoid"]
Printer = Literal["color", "black_and_white"]
Paper = Literal["A4", "Letter"]
VisualStyle = Literal["auto", "vintage", "noir", "modern", "victorian", "scifi", "fantasy", "kids", "minimal"]
ImageKind = Literal["svg", "none"]
Quality = Literal["fast", "best"]
ConceptPicker = Literal["ask", "agent"]


class FrozenConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PlayersConfig(FrozenConfigModel):
    count: int
    names: tuple[str, ...]


class ThemeConfig(FrozenConfigModel):
    idea: str
    tone: Tone
    era: Era


class ContentConfig(FrozenConfigModel):
    death_allowed: bool
    scary_level: ScaryLevel
    reading_load: ReadingLoad


class PersonalizationConfig(FrozenConfigModel):
    host_name: str
    place: str
    inside_jokes: tuple[str, ...]
    dedication: str


class PuzzlePreferencesConfig(FrozenConfigModel):
    words: PuzzlePreference
    numbers: PuzzlePreference
    logic: PuzzlePreference
    visual: PuzzlePreference
    crafts: PuzzlePreference
    deduction: PuzzlePreference


class EquipmentConfig(FrozenConfigModel):
    printer: Printer
    ink_saving: bool
    paper: Paper
    scissors: bool
    tape_or_glue: bool
    envelopes: bool


class AssistanceConfig(FrozenConfigModel):
    hints: bool
    paper_answer_check: bool
    companion_page: bool


class VisualsConfig(FrozenConfigModel):
    style: VisualStyle
    images: ImageKind
    readable_font: bool


class GenerationConfig(FrozenConfigModel):
    quality: Quality
    pick_concept: ConceptPicker
    seed: int


class OutputConfig(FrozenConfigModel):
    folder: str


class GameConfig(FrozenConfigModel):
    schema_version: Literal[1]
    audience: Audience
    format: GameFormat
    players: PlayersConfig
    host: HostRole
    duration_minutes: int
    difficulty: Difficulty
    language: Language
    theme: ThemeConfig
    content: ContentConfig
    personalization: PersonalizationConfig
    puzzle_preferences: PuzzlePreferencesConfig
    equipment: EquipmentConfig
    assistance: AssistanceConfig
    visuals: VisualsConfig
    generation: GenerationConfig
    output: OutputConfig


class ConfigFinding(BaseModel):
    """One problem in a config. `path` is dotted ("players.names.2"); the empty path is the whole config."""

    model_config = ConfigDict(frozen=True)

    path: str
    message: str
    rule: str


class ConfigLoadResult(BaseModel):
    """The typed config when the raw config is valid, else `None` and at least one finding."""

    model_config = ConfigDict(frozen=True)

    config: GameConfig | None
    findings: list[ConfigFinding]


@cache
def load_config_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(CONFIG_SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema


def apply_schema_defaults(schema: dict[str, Any], value: Any) -> Any:
    """Return a deep copy of `value` where each missing property with a `default` takes it, at every depth."""
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    properties: dict[str, Any] = schema.get("properties", {})
    filled: dict[str, Any] = {}
    for key, property_schema in properties.items():
        if key in value:
            filled[key] = apply_schema_defaults(property_schema, value[key])
        elif "default" in property_schema:
            filled[key] = apply_schema_defaults(property_schema, property_schema["default"])
    for key, item in value.items():
        if key not in properties:
            filled[key] = copy.deepcopy(item)
    return filled


def join_path(parts: list[str | int]) -> str:
    return ".".join(str(part) for part in parts)


def findings_from_error(error: ValidationError) -> list[ConfigFinding]:
    # jsonschema reports an unknown key and a missing required key at the parent object. The configurator shows
    # each problem next to its own field, so both sides report these two at the path of the key itself.
    parent: list[str | int] = list(error.absolute_path)
    rule: str = f"config.{error.validator}"
    instance: Any = error.instance
    if error.validator == "additionalProperties":
        object_schema: Any = error.schema
        known: dict[str, Any] = object_schema["properties"]
        return [
            ConfigFinding(path=join_path([*parent, key]), message=f"The key '{key}' is not allowed here.", rule=rule)
            for key in instance
            if key not in known
        ]
    if error.validator == "required":
        required_keys: Any = error.validator_value
        return [
            ConfigFinding(path=join_path([*parent, key]), message=f"The key '{key}' is required.", rule=rule)
            for key in required_keys
            if key not in instance
        ]
    return [ConfigFinding(path=join_path(parent), message=error.message, rule=rule)]


def normalize_config(raw: object) -> ConfigLoadResult:
    """Validate a parsed config against the schema, then fill every default and build the typed model."""
    schema: dict[str, Any] = load_config_schema()
    findings: list[ConfigFinding] = [
        finding for error in Draft202012Validator(schema).iter_errors(raw) for finding in findings_from_error(error)
    ]
    if findings:
        return ConfigLoadResult(
            config=None, findings=sorted(findings, key=lambda finding: (finding.path, finding.rule))
        )
    config: GameConfig = GameConfig.model_validate(apply_schema_defaults(schema, raw))
    return ConfigLoadResult(config=config, findings=[])


def load_config_file(path: Path) -> ConfigLoadResult:
    """Read a config file as UTF-8 JSON and normalize it. Text that is not JSON gives one `config.json` finding."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return ConfigLoadResult(
            config=None,
            findings=[ConfigFinding(path="", message=f"The file is not valid JSON: {error}", rule="config.json")],
        )
    return normalize_config(raw)
