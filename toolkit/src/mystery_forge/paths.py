"""Folders on the user's computer, and names that are safe for them.

The default output folder is the user's real Desktop. On Windows, OneDrive often moves the Desktop (for example to
`OneDrive\\Escritorio`), so `~/Desktop` can be wrong: Windows itself knows the real place (a "known folder"). On Linux
the place is in `~/.config/user-dirs.dirs`. Every lookup takes its system dependency as a parameter, so the tests run
every branch on every operating system.
"""

import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

# A browser names a second download "x.mystery-config (1).json" (Chrome, Edge) or "x.mystery-config(1).json" (Firefox).
CONFIG_FILE_NAME: re.Pattern[str] = re.compile(r"\.mystery-config(?: ?\(\d+\))?\.json$")
MAX_FOLDER_NAME: int = 60
MAX_SLUG: int = 48
FORBIDDEN_CHARACTERS: re.Pattern[str] = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_WINDOWS_NAMES: frozenset[str] = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{digit}" for digit in range(1, 10)), *(f"lpt{digit}" for digit in range(1, 10))}
)
XDG_LINE: re.Pattern[str] = re.compile(r'^(XDG_[A-Z]+_DIR)="?([^"]*)"?\s*$')

type KnownFolderReader = Callable[[str], str | None]


@dataclass(frozen=True)
class SystemFolders:
    desktop: Path
    downloads: Path


def system_folders(
    platform: str, home: Path, environment: Mapping[str, str], read_known_folder: KnownFolderReader
) -> SystemFolders:
    """Find the Desktop and Downloads folders. `platform` is a `sys.platform` value."""
    default = SystemFolders(desktop=home / "Desktop", downloads=home / "Downloads")
    if platform == "win32":
        desktop: str | None = read_known_folder("Desktop")
        downloads: str | None = read_known_folder("Downloads")
        return SystemFolders(
            desktop=Path(desktop) if desktop else default.desktop,
            downloads=Path(downloads) if downloads else default.downloads,
        )
    if platform.startswith("linux"):
        config_home: Path = Path(environment.get("XDG_CONFIG_HOME", str(home / ".config")))
        user_dirs_file: Path = config_home / "user-dirs.dirs"
        if user_dirs_file.is_file():
            entries: dict[str, Path] = parse_xdg_user_dirs(user_dirs_file.read_text(encoding="utf-8"), home)
            return SystemFolders(
                desktop=entries.get("XDG_DESKTOP_DIR", default.desktop),
                downloads=entries.get("XDG_DOWNLOAD_DIR", default.downloads),
            )
    return default


def parse_xdg_user_dirs(text: str, home: Path) -> dict[str, Path]:
    entries: dict[str, Path] = {}
    for line in text.splitlines():
        match: re.Match[str] | None = XDG_LINE.match(line.strip())
        if match is not None:
            entries[match.group(1)] = Path(match.group(2).replace("$HOME", str(home)))
    return entries


def read_windows_known_folder(name: str) -> str | None:  # pragma: no cover - a Windows system call, tested by hand
    """Ask Windows for the real path of a known folder ("Desktop" or "Downloads")."""
    import ctypes
    import uuid
    from ctypes import wintypes

    folder_ids: dict[str, str] = {
        "Desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
        "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    }

    class Guid(ctypes.Structure):
        _fields_ = [
            ("data1", wintypes.DWORD),
            ("data2", wintypes.WORD),
            ("data3", wintypes.WORD),
            ("data4", wintypes.BYTE * 8),
        ]

    parsed = uuid.UUID(folder_ids[name])
    guid = Guid(parsed.fields[0], parsed.fields[1], parsed.fields[2], (wintypes.BYTE * 8)(*parsed.bytes[8:]))
    path_pointer = ctypes.c_wchar_p()
    windll = ctypes.windll  # type: ignore[attr-defined,unused-ignore]  # only Windows stubs have windll
    if windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path_pointer)) != 0:
        return None
    path: str | None = path_pointer.value
    windll.ole32.CoTaskMemFree(path_pointer)
    return path


def safe_folder_name(title: str) -> str:
    """Turn a game title into a folder name that works on Windows, macOS, and Linux."""
    # The forbidden characters include ":", so keep a subtitle break visible: "Tape Seven - The Clock".
    dashed: str = title.replace(": ", " - ").replace(":", "-")
    cleaned: str = FORBIDDEN_CHARACTERS.sub(lambda match: " " if match.group(0) in "\t\n\r" else "", dashed)
    collapsed: str = " ".join(cleaned.split())
    if len(collapsed) > MAX_FOLDER_NAME:
        cut: str = collapsed[:MAX_FOLDER_NAME]
        collapsed = cut.rsplit(" ", 1)[0] if " " in cut else cut
    collapsed = collapsed.rstrip(". ")
    if not collapsed:
        return "Mystery game"
    if collapsed.lower() in RESERVED_WINDOWS_NAMES:
        return f"{collapsed} game"
    return collapsed


def slugify(title: str) -> str:
    """Turn a title into a short ASCII folder id, such as `the-lens-of-gull-rock`."""
    ascii_text: str = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    slug: str = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:MAX_SLUG].rstrip("-") or "game"


def unique_folder(parent: Path, name: str) -> Path:
    """Return `parent/name`, or `parent/name (2)` and so on when the name is taken. Never overwrite a game."""
    candidate: Path = parent / name
    number: int = 2
    while candidate.exists():
        candidate = parent / f"{name} ({number})"
        number += 1
    return candidate


def newest_config_file(folder: Path) -> Path | None:
    """Return the newest `*.mystery-config.json` file in a folder (usually Downloads), or None."""
    if not folder.is_dir():
        return None
    configs: list[Path] = [path for path in folder.iterdir() if CONFIG_FILE_NAME.search(path.name)]
    if not configs:
        return None
    return max(configs, key=lambda path: path.stat().st_mtime)
