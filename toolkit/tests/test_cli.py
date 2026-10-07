import io
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from mystery_forge import cli
from mystery_forge.cli_output import MAX_FINDINGS_IN_OUTPUT
from mystery_forge.paths import SystemFolders

GOLDEN_GAME: Path = Path(__file__).parent / "fixtures" / "golden"


def run(argv: list[str], monkeypatch: pytest.MonkeyPatch, folders: SystemFolders | None = None) -> tuple[int, Any]:
    output = io.StringIO()
    if folders is not None:
        monkeypatch.setattr(cli, "find_system_folders", lambda: folders)
    code: int = cli.main(argv, output)
    text: str = output.getvalue()
    try:
        return code, json.loads(text)
    except json.JSONDecodeError:
        return code, text


@pytest.fixture
def folders(tmp_path: Path) -> SystemFolders:
    desktop = tmp_path / "Desktop"
    downloads = tmp_path / "Downloads"
    desktop.mkdir()
    downloads.mkdir()
    return SystemFolders(desktop=desktop, downloads=downloads)


def write_config(folder: Path, name: str = "party.mystery-config.json", **overrides: Any) -> Path:
    config: dict[str, Any] = {"schema_version": 1, "theme": {"idea": "A heist on a night train"}}
    config.update(overrides)
    path = folder / name
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_setup_uses_the_newest_config_in_downloads_and_writes_the_game_folder(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config(folders.downloads, generation={"seed": 42})
    games = tmp_path / "games"
    code, result = run(["setup", "--games-dir", str(games)], monkeypatch, folders)
    assert code == 0
    assert result["ok"] is True
    game_dir = Path(result["game_dir"])
    assert game_dir.parent == games
    assert "a-heist-on-a-night-train" in game_dir.name
    source = game_dir / "source"
    assert json.loads((source / "config.json").read_text(encoding="utf-8"))["generation"]["seed"] == 42
    assert json.loads((source / "brief.json").read_text(encoding="utf-8"))["seed"] == 42
    draw = json.loads((source / "draw.json").read_text(encoding="utf-8"))
    assert len(draw["settings"]) == 3
    assert result["config_file"].endswith("party.mystery-config.json")
    assert result["brief"]["puzzle_count"] > 0
    assert result["summary"]["language"] == "en"
    assert result["summary"]["pick_concept"] == "ask"
    assert result["summary"]["host"] == "self_running"
    assert result["summary"]["images"] == "svg"


def test_setup_with_an_explicit_config_and_a_random_seed(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = write_config(tmp_path, "mine.json", language="es")
    monkeypatch.setattr(cli, "random_seed", lambda: 777)
    code, result = run(
        ["setup", "--config", str(config_path), "--games-dir", str(tmp_path / "g")], monkeypatch, folders
    )
    assert code == 0
    assert result["brief"]["seed"] == 777
    assert result["summary"]["language"] == "es"


def test_setup_without_any_config_reports_it(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, result = run(["setup", "--games-dir", str(tmp_path / "g")], monkeypatch, folders)
    assert code == 0
    assert result["ok"] is False
    assert result["findings"][0]["rule"] == "config.not_found"


def test_setup_with_defaults_needs_no_file(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, result = run(["setup", "--defaults", "--games-dir", str(tmp_path / "g")], monkeypatch, folders)
    assert code == 0
    assert result["ok"] is True
    assert result["config_file"] is None


def test_setup_reports_an_invalid_config(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = write_config(tmp_path, "bad.json", players={"count": 99})
    code, result = run(
        ["setup", "--config", str(config_path), "--games-dir", str(tmp_path / "g")], monkeypatch, folders
    )
    assert code == 0
    assert result["ok"] is False
    assert result["findings"][0]["path"] == "players.count"


def test_setup_with_a_missing_config_file_is_a_usage_error(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, result = run(["setup", "--config", str(tmp_path / "nope.json")], monkeypatch, folders)
    assert code == 2
    assert result["ok"] is False


def test_setup_avoids_the_settings_of_earlier_games(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config(folders.downloads, generation={"seed": 5})
    games = tmp_path / "games"
    _, first = run(["setup", "--games-dir", str(games)], monkeypatch, folders)
    _, second = run(["setup", "--games-dir", str(games)], monkeypatch, folders)
    first_settings = {item["id"] for item in json.loads(Path(first["draw_file"]).read_text("utf-8"))["settings"]}
    second_settings = {item["id"] for item in json.loads(Path(second["draw_file"]).read_text("utf-8"))["settings"]}
    assert not first_settings & second_settings
    assert first["game_dir"] != second["game_dir"]


def test_assemble_writes_game_json_and_reports_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "source")
    code, result = run(["assemble", "--game", str(tmp_path)], monkeypatch)
    assert code == 0
    assert (tmp_path / "game.json").is_file() == (result["game_written"] is True)
    assert result["errors"] == len([f for f in result["findings"] if f["severity"] == "error"])
    assert Path(result["report"]).is_file()


def test_assemble_of_a_folder_with_an_empty_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "source").mkdir()
    code, result = run(["assemble", "--game", str(tmp_path)], monkeypatch)
    assert code == 0
    assert result["ok"] is False
    assert result["game_written"] is False


def test_findings_in_the_output_are_capped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shutil.copytree(GOLDEN_GAME / "source", tmp_path / "source")
    documents = tmp_path / "source" / "documents"
    for index in range(30):
        (documents / f"D{index + 10}.md").write_text("no front matter", encoding="utf-8")
    _, result = run(["assemble", "--game", str(tmp_path)], monkeypatch)
    assert len(result["findings"]) == MAX_FINDINGS_IN_OUTPUT
    assert result["more_findings"] > 0


def test_catalog_list_and_show(monkeypatch: pytest.MonkeyPatch) -> None:
    code, listing = run(["catalog", "list"], monkeypatch)
    assert code == 0
    assert any(item["id"] == "caesar-cipher" for item in listing["mechanics"])
    code, implemented = run(["catalog", "list", "--implemented"], monkeypatch)
    assert all(item["implemented"] or item["verification"] == "panel" for item in implemented["mechanics"])
    code, shown = run(["catalog", "show", "caesar-cipher"], monkeypatch)
    assert code == 0
    assert shown["mechanic"]["id"] == "caesar-cipher"
    assert "shift" in json.dumps(shown["params_schema"])
    code, missing = run(["catalog", "show", "caesar"], monkeypatch)
    assert code == 2
    assert "caesar-cipher" in missing["message"]


def test_catalog_show_of_a_panel_mechanic_has_no_params(monkeypatch: pytest.MonkeyPatch) -> None:
    code, shown = run(["catalog", "show", "riddle"], monkeypatch)
    assert code == 0
    assert shown["implemented"] is True


def test_catalog_design_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    code, text = run(["catalog", "rules"], monkeypatch)
    assert code == 0
    assert isinstance(text, str)
    assert len(text) > 500


@pytest.mark.parametrize("name", ["story", "flow", "puzzle", "document"])
def test_schema_prints_the_json_schema_of_each_source_file(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    code, schema = run(["schema", name], monkeypatch)
    assert code == 0
    assert schema["type"] == "object"


def test_schema_references_lists_the_reference_forms_and_directives(monkeypatch: pytest.MonkeyPatch) -> None:
    code, result = run(["schema", "references"], monkeypatch)
    assert code == 0
    assert "{{char:<id>}}" in result["references"]
    assert "handwriting" in result["directives"]


def test_doctor_reports_the_browser_and_folders(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "probe_browser", lambda: "chrome")
    code, result = run(["doctor"], monkeypatch, folders)
    assert code == 0
    assert result["ok"] is True
    assert result["browser"] == "chrome"
    assert result["desktop"] == str(folders.desktop)
    monkeypatch.setattr(cli, "probe_browser", lambda: None)
    code, result = run(["doctor"], monkeypatch, folders)
    assert result["ok"] is False
    assert "playwright install chromium" in result["fix"]


def test_unknown_command_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["no-such-verb"], io.StringIO())
    assert raised.value.code == 2


def test_main_writes_to_stdout_by_default(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["schema", "flow"]) == 0
    assert json.loads(capsys.readouterr().out)["type"] == "object"


def test_find_system_folders_and_random_seed_use_the_real_system() -> None:
    assert isinstance(cli.find_system_folders(), SystemFolders)
    seed = cli.random_seed()
    assert 1 <= seed <= 2_147_483_647


def test_setup_accepts_the_word_defaults_as_the_config(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, result = run(["setup", "--config", "defaults", "--games-dir", str(tmp_path / "g")], monkeypatch, folders)
    assert code == 0
    assert result["ok"] is True
    assert result["config_file"] is None


def test_setup_skips_a_broken_draw_of_an_earlier_crashed_setup(
    tmp_path: Path, folders: SystemFolders, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config(folders.downloads, generation={"seed": 5})
    games = tmp_path / "games"
    for name, text in (("crashed", "{not json"), ("odd", '{"settings": [1]}'), ("empty", "{}")):
        (games / name / "source").mkdir(parents=True)
        (games / name / "source" / "draw.json").write_text(text, encoding="utf-8")
    code, result = run(["setup", "--games-dir", str(games)], monkeypatch, folders)
    assert code == 0
    assert result["ok"] is True


def test_main_reads_stdin_as_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli.main(["schema", "flow"], io.StringIO()) == 0
    assert stdin.encoding == "utf-8"


def test_a_crash_inside_a_verb_is_one_json_line_with_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*arguments: Any) -> Any:
        raise KeyError("lost")

    monkeypatch.setattr(cli, "assemble_game", explode)
    (tmp_path / "source").mkdir()
    code, result = run(["assemble", "--game", str(tmp_path)], monkeypatch)
    assert code == 2
    assert result == {"ok": False, "message": "KeyError: 'lost'"}
