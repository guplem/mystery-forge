"""One year style per game: the documents count years the same way as the dates that the toolkit prints.

A Japanese story often writes era years (昭和33年), while the toolkit fills `{{event:...}}` dates and header dates from
the language pack's date pattern. When the two styles differ, players may think that two different years are meant.
The pattern prints Western years with {year}, or era years with {era_year}.
"""

import re
from typing import Final

from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.i18n import uses_era_years

# ASCII and full-width digits, as a regular expression character range.
DIGITS: Final[str] = f"0-9{chr(0xFF10)}-{chr(0xFF19)}"
ERA_YEAR: Final[re.Pattern[str]] = re.compile(
    rf"(?:明治|大正|昭和|平成|令和)\s*(?:[{DIGITS}]+|元|[一二三四五六七八九十]+)\s*年"
)
WESTERN_YEAR: Final[re.Pattern[str]] = re.compile(rf"(?<![{DIGITS}])[{DIGITS}]{{4}}\s*年")


def check_calendar(game: Game) -> list[Finding]:
    era_pattern: bool = uses_era_years(game.config.language)
    other_style: re.Pattern[str] = WESTERN_YEAR if era_pattern else ERA_YEAR
    printed: str = "era years (昭和33年)" if era_pattern else "Western years (1958年)"
    findings: list[Finding] = []
    for document in game.documents:
        match: re.Match[str] | None = other_style.search(document.text)
        if match is not None:
            findings.append(
                Finding(
                    severity="error",
                    rule="dates.mixed_year_style",
                    message=f"The document {document.meta.id} writes '{match.group(0)}', but the toolkit prints the "
                    f"dates of this game with {printed}.",
                    file=document.file,
                    fix_hint="Use one year style in the whole game: rewrite the year in the style of the toolkit "
                    "dates, or change date_pattern in source/strings.json ({year} for Western years, {era_year} for "
                    "era years) and rewrite the other documents to match.",
                )
            )
    return findings
