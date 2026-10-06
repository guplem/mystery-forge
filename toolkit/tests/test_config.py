import json
import typing
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from mystery_forge.config import (
    CONFIG_SCHEMA_PATH,
    ConfigFinding,
    GameConfig,
    apply_schema_defaults,
    load_config_file,
    normalize_config,
)

CONTRACTS_PATH: Path = Path(__file__).resolve().parents[2] / "contracts"
VECTORS: dict[str, Any] = json.loads((CONTRACTS_PATH / "config-vectors.json").read_text(encoding="utf-8"))
SCHEMA: dict[str, Any] = json.loads((CONTRACTS_PATH / "game-config.schema.json").read_text(encoding="utf-8"))


def read_dotted_path(document: dict[str, Any], dotted_path: str) -> Any:
    value: Any = document
    for key in dotted_path.split("."):
        value = value[key]
    return value


def test_the_schema_path_points_at_the_contract_file() -> None:
    assert CONFIG_SCHEMA_PATH == CONTRACTS_PATH / "game-config.schema.json"


@pytest.mark.parametrize("vector", VECTORS["valid"], ids=lambda vector: vector["name"])
def test_a_valid_vector_gives_no_finding_and_the_expected_defaults(vector: dict[str, Any]) -> None:
    result = normalize_config(vector["config"])
    assert result.findings == []
    assert result.config is not None
    dumped: dict[str, Any] = result.config.model_dump(mode="json")
    for dotted_path, expected in vector["normalized_summary"].items():
        assert read_dotted_path(dumped, dotted_path) == expected, dotted_path


@pytest.mark.parametrize("vector", VECTORS["invalid"], ids=lambda vector: vector["name"])
def test_an_invalid_vector_gives_findings_at_exactly_the_expected_paths(vector: dict[str, Any]) -> None:
    result = normalize_config(vector["config"])
    assert result.config is None
    assert sorted({finding.path for finding in result.findings}) == vector["error_paths"]
    for finding in result.findings:
        assert finding.rule.startswith("config.")
        assert finding.message


def test_a_finding_names_the_schema_keyword_that_failed() -> None:
    result = normalize_config({"schema_version": 1, "players": {"count": 0, "nickname": "x"}})
    assert sorted(result.findings, key=lambda finding: finding.path) == [
        ConfigFinding(path="players.count", message="0 is less than the minimum of 1", rule="config.minimum"),
        ConfigFinding(
            path="players.nickname",
            message="The key 'nickname' is not allowed here.",
            rule="config.additionalProperties",
        ),
    ]


def test_a_missing_required_key_is_reported_at_its_own_path() -> None:
    result = normalize_config({})
    assert result.findings == [
        ConfigFinding(path="schema_version", message="The key 'schema_version' is required.", rule="config.required")
    ]


def test_the_defaults_do_not_change_the_raw_config() -> None:
    raw: dict[str, Any] = {"schema_version": 1, "players": {"count": 2}}
    normalize_config(raw)
    assert raw == {"schema_version": 1, "players": {"count": 2}}


def test_apply_schema_defaults_keeps_unknown_keys_and_skips_a_key_without_a_default() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"required_key": {"type": "integer"}, "filled": {"type": "string", "default": "x"}},
    }
    assert apply_schema_defaults(schema, {"unknown": [1]}) == {"filled": "x", "unknown": [1]}
    assert apply_schema_defaults(schema, 5) == 5


def test_the_config_model_is_frozen() -> None:
    config = normalize_config({"schema_version": 1}).config
    assert config is not None
    with pytest.raises(ValueError, match="frozen"):
        config.audience = "kids"  # type: ignore[misc]


def assert_model_matches_schema(model: type[BaseModel], schema: dict[str, Any]) -> None:
    properties: dict[str, Any] = schema["properties"]
    assert set(model.model_fields) == set(properties), model.__name__
    for name, field in model.model_fields.items():
        property_schema: dict[str, Any] = properties[name]
        annotation: Any = field.annotation
        if property_schema["type"] == "object":
            assert_model_matches_schema(annotation, property_schema)
        elif "enum" in property_schema:
            assert typing.get_origin(annotation) is typing.Literal, name
            assert list(typing.get_args(annotation)) == property_schema["enum"], name


def test_the_pydantic_model_has_the_same_fields_and_enums_as_the_schema() -> None:
    assert_model_matches_schema(GameConfig, SCHEMA)


def test_load_config_file_reads_utf8_text(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"schema_version": 1, "players": {"names": ["Núria", "Çelik"]}}, ensure_ascii=False),
        encoding="utf-8",
    )
    result = load_config_file(config_path)
    assert result.findings == []
    assert result.config is not None
    assert result.config.players.names == ("Núria", "Çelik")


def test_load_config_file_reports_text_that_is_not_json(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "config.json"
    config_path.write_text("{ not json", encoding="utf-8")
    result = load_config_file(config_path)
    assert result.config is None
    assert len(result.findings) == 1
    finding: ConfigFinding = result.findings[0]
    assert finding.path == ""
    assert finding.rule == "config.json"
    assert "line 1" in finding.message
