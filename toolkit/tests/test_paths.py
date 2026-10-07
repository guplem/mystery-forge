import os
from pathlib import Path

import pytest

from mystery_forge.paths import (
    SystemFolders,
    newest_config_file,
    parse_xdg_user_dirs,
    safe_folder_name,
    slugify,
    system_folders,
    unique_folder,
)


def no_known_folder(name: str) -> str | None:
    return None


def test_windows_uses_the_known_folder_even_when_onedrive_moved_it(tmp_path: Path) -> None:
    desktop = tmp_path / "OneDrive" / "Escritorio"
    downloads = tmp_path / "Descargas"
    known = {"Desktop": str(desktop), "Downloads": str(downloads)}
    folders = system_folders("win32", tmp_path, {}, known.get)
    assert folders == SystemFolders(desktop=desktop, downloads=downloads)


def test_windows_falls_back_to_the_home_folders_when_the_lookup_fails(tmp_path: Path) -> None:
    folders = system_folders("win32", tmp_path, {}, no_known_folder)
    assert folders == SystemFolders(desktop=tmp_path / "Desktop", downloads=tmp_path / "Downloads")


def test_macos_uses_the_home_folders(tmp_path: Path) -> None:
    folders = system_folders("darwin", tmp_path, {}, no_known_folder)
    assert folders == SystemFolders(desktop=tmp_path / "Desktop", downloads=tmp_path / "Downloads")


def test_linux_reads_the_xdg_user_dirs_file(tmp_path: Path) -> None:
    config_home = tmp_path / "config"
    config_home.mkdir()
    (config_home / "user-dirs.dirs").write_text(
        '# comment\nXDG_DESKTOP_DIR="$HOME/Escritorio"\nXDG_DOWNLOAD_DIR="/data/descargas"\n', encoding="utf-8"
    )
    folders = system_folders("linux", tmp_path, {"XDG_CONFIG_HOME": str(config_home)}, no_known_folder)
    assert folders == SystemFolders(desktop=tmp_path / "Escritorio", downloads=Path("/data/descargas"))


def test_linux_without_a_user_dirs_file_uses_the_home_folders(tmp_path: Path) -> None:
    folders = system_folders("linux", tmp_path, {}, no_known_folder)
    assert folders == SystemFolders(desktop=tmp_path / "Desktop", downloads=tmp_path / "Downloads")


def test_parse_xdg_user_dirs_ignores_noise_and_expands_home(tmp_path: Path) -> None:
    text = 'XDG_DESKTOP_DIR="$HOME/D"\nbroken line\nXDG_MUSIC_DIR="$HOME/M"\nXDG_DOWNLOAD_DIR=$HOME/X\n'
    assert parse_xdg_user_dirs(text, tmp_path) == {
        "XDG_DESKTOP_DIR": tmp_path / "D",
        "XDG_MUSIC_DIR": tmp_path / "M",
        "XDG_DOWNLOAD_DIR": tmp_path / "X",
    }


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("The Lens of Gull Rock", "The Lens of Gull Rock"),
        ('Who stole "the" lens? A/B: test*', "Who stole the lens AB - test"),
        ("Tape Seven: The Clock", "Tape Seven - The Clock"),
        ("Case 12:30", "Case 12-30"),
        ("El Faro de Señora García", "El Faro de Señora García"),
        ("Ends with dots...  ", "Ends with dots"),
        ("CON", "CON game"),
        ("lpt1", "lpt1 game"),
        ("   ", "Mystery game"),
        ("a\tb\nc", "a b c"),
        ("x" * 80, "x" * 60),
        ("word " * 20, "word word word word word word word word word word word word"),
    ],
)
def test_safe_folder_name(title: str, expected: str) -> None:
    assert safe_folder_name(title) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("The Lens of Gull Rock", "the-lens-of-gull-rock"),
        ("¿Quién robó el Faro?", "quien-robo-el-faro"),
        ("!!!", "game"),
        ("a" * 70, "a" * 48),
    ],
)
def test_slugify(title: str, expected: str) -> None:
    assert slugify(title) == expected


def test_unique_folder_adds_a_number_when_the_name_is_taken(tmp_path: Path) -> None:
    assert unique_folder(tmp_path, "Game") == tmp_path / "Game"
    (tmp_path / "Game").mkdir()
    (tmp_path / "Game (2)").mkdir()
    assert unique_folder(tmp_path, "Game") == tmp_path / "Game (3)"


def test_newest_config_file_picks_the_latest_mystery_config(tmp_path: Path) -> None:
    assert newest_config_file(tmp_path / "missing") is None
    assert newest_config_file(tmp_path) is None
    old = tmp_path / "old.mystery-config.json"
    new = tmp_path / "new.mystery-config.json"
    other = tmp_path / "notes.json"
    for index, path in enumerate((old, new, other)):
        path.write_text("{}", encoding="utf-8")
        os.utime(path, (1_000_000 + index, 1_000_000 + index))
    assert newest_config_file(tmp_path) == new


@pytest.mark.parametrize("name", ["party.mystery-config (1).json", "party.mystery-config(2).json"])
def test_newest_config_file_matches_a_downloaded_copy(tmp_path: Path, name: str) -> None:
    old = tmp_path / "party.mystery-config.json"
    copy = tmp_path / name
    for index, path in enumerate((old, copy, tmp_path / "party.mystery-config (x).json")):
        path.write_text("{}", encoding="utf-8")
        os.utime(path, (1_000_000 + index, 1_000_000 + index))
    assert newest_config_file(tmp_path) == copy
