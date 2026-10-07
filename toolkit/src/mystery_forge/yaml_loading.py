"""YAML loading for the game source files that agents write.

Every scalar loads as text, except an unquoted `null` or `~`. YAML 1.1 loaders change values silently (`answer: no`
becomes False, `answer: 0420` becomes 272), and a printed code with a lost leading zero is a broken puzzle. Pydantic
converts each text value to the type that its model declares. The loader also records the line of every value, so
error messages can point an agent at the exact line to fix.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml

type YamlPath = tuple[str | int, ...]

NULL_TAG: str = "tag:yaml.org,2002:null"
NULL_SPELLINGS: frozenset[str] = frozenset({"null", "Null", "NULL", "~", ""})
# Windows editors may start a UTF-8 file with this mark. It is not text, and it hides a first line `---`.
BYTE_ORDER_MARK: Final[str] = "\ufeff"


class YamlLoadError(Exception):
    """A YAML text that cannot load. `line` is 1-based when known."""

    def __init__(self, source: str, message: str, line: int | None) -> None:
        super().__init__(message)
        self.source: str = source
        self.message: str = message
        self.line: int | None = line

    def __str__(self) -> str:
        where: str = f"{self.source}:{self.line}" if self.line is not None else self.source
        return f"{where}: {self.message}"


@dataclass(frozen=True)
class YamlDocument:
    """Loaded data plus the 1-based line of each value, by path."""

    data: Any
    lines: dict[YamlPath, int]

    def line_of(self, path: YamlPath) -> int | None:
        """Return the line of a path, or of its nearest parent that has a line."""
        for length in range(len(path), 0, -1):
            line: int | None = self.lines.get(path[:length])
            if line is not None:
                return line
        return None


def parse_yaml_text(text: str, source: str) -> YamlDocument:
    """Parse one YAML document where every scalar is text, and record the line of every value."""
    try:
        root: yaml.Node | None = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.MarkedYAMLError as error:
        line: int | None = error.problem_mark.line + 1 if error.problem_mark is not None else None
        raise YamlLoadError(source, f"invalid YAML: {error.problem}", line) from error
    except yaml.YAMLError as error:
        # A reader error (a control character, for example) carries no mark.
        raise YamlLoadError(source, f"invalid YAML: {error}", None) from error
    lines: dict[YamlPath, int] = {}
    if root is None:
        return YamlDocument(data=None, lines=lines)
    return YamlDocument(data=_convert(root, (), lines, source), lines=lines)


def _convert(node: yaml.Node, path: YamlPath, lines: dict[YamlPath, int], source: str) -> Any:
    if path:
        lines[path] = node.start_mark.line + 1
    if isinstance(node, yaml.MappingNode):
        return _convert_mapping(node, path, lines, source)
    if isinstance(node, yaml.SequenceNode):
        return [_convert(item, (*path, index), lines, source) for index, item in enumerate(node.value)]
    scalar: str = str(node.value)
    is_plain_null: bool = node.tag == NULL_TAG and scalar in NULL_SPELLINGS
    return None if is_plain_null else scalar


def _convert_mapping(node: yaml.MappingNode, path: YamlPath, lines: dict[YamlPath, int], source: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        if not isinstance(key_node, yaml.ScalarNode):
            raise YamlLoadError(source, "a mapping key must be plain text", key_node.start_mark.line + 1)
        key: str = str(key_node.value)
        if key in result:
            raise YamlLoadError(source, f"the key '{key}' appears twice", key_node.start_mark.line + 1)
        result[key] = _convert(value_node, (*path, key), lines, source)
    return result


def split_front_matter(text: str) -> tuple[str | None, str, int]:
    """Split a Markdown file into its YAML front matter, its body, and the 1-based line where the body starts.

    The front matter sits between a first line `---` and the next line `---`. A file without it has no header.
    """
    normalized: str = text.removeprefix(BYTE_ORDER_MARK).replace("\r\n", "\n")
    all_lines: list[str] = normalized.split("\n")
    if not all_lines or all_lines[0].strip() != "---":
        return None, normalized, 1
    for index in range(1, len(all_lines)):
        if all_lines[index].strip() == "---":
            header: str = "\n".join(all_lines[1:index]) + "\n"
            body: str = "\n".join(all_lines[index + 1 :])
            return header, body, index + 2
    raise YamlLoadError("front matter", "the front matter has no closing '---' line", 1)


def read_source_text(path: Path) -> str:
    """Read a source file as UTF-8 without its byte order mark. Raise `UnicodeDecodeError` for other bytes."""
    return path.read_text(encoding="utf-8-sig")
