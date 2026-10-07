"""The fact registry: names spelled one way only, and a timeline where nobody is in two places at once.

An agent that retypes a name instead of `{{char:id}}` often misspells it ("Margret Hale"). Players then wonder if a
new person appears. The timeline is the truth of the story, so a person in two places at once is a plot hole.
"""

import re
from datetime import datetime
from typing import Final

from mystery_forge.checks.game_index import STORY_FILE
from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.spec.models import TimelineEvent

WORD_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^\W\d_]+")
# Gaps that keep two capitalized words in one name: spaces only, so a comma or a line break ends the name.
NAME_GAP_PATTERN: Final[re.Pattern[str]] = re.compile(r"[ \t]+")
MIN_NAME_LENGTH: Final[int] = 4
LONG_NAME_LENGTH: Final[int] = 5


def check_fact_registry(game: Game) -> list[Finding]:
    return [*near_name_findings(game), *timeline_reference_findings(game), *two_places_findings(game)]


def edit_distance(first: str, second: str) -> int:
    """Return the Levenshtein distance: the fewest letter insertions, deletions, and changes between two texts."""
    previous: list[int] = list(range(len(second) + 1))
    for row, first_letter in enumerate(first, start=1):
        current: list[int] = [row]
        for column, second_letter in enumerate(second, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (first_letter != second_letter),
                )
            )
        previous = current
    return previous[-1]


def allowed_distance(name: str) -> int:
    if len(name) >= LONG_NAME_LENGTH:
        return 2
    return 1 if len(name) == MIN_NAME_LENGTH else 0


def capitalized_runs(text: str) -> list[list[str]]:
    """Split a text into runs of capitalized words of 2 or more letters that only spaces separate."""
    runs: list[list[str]] = []
    current: list[str] = []
    last_end: int = 0
    for match in WORD_PATTERN.finditer(text):
        word: str = match.group(0)
        if not (word[0].isupper() and len(word) >= 2):
            current = []
            continue
        if not (current and NAME_GAP_PATTERN.fullmatch(text[last_end : match.start()])):
            current = []
            runs.append(current)
        current.append(word)
        last_end = match.end()
    return runs


def registry_spellings(game: Game) -> dict[str, str]:
    """Map each registry name and alias, casefolded, to its spelling in story.yaml."""
    texts: list[str] = [
        *(name for character in game.story.characters for name in (character.name, *character.aliases)),
        *(location.name for location in game.story.locations),
        *(story_object.name for story_object in game.story.objects),
    ]
    return {text.casefold(): text for text in texts}


def near_name_findings(game: Game) -> list[Finding]:
    spellings: dict[str, str] = registry_spellings(game)
    comparable: list[str] = [name for name in spellings if allowed_distance(name) > 0]
    # A first name or a surname alone is a correct short form of a registry name, never a misspelling.
    name_parts: set[str] = {part for name in spellings for part in name.split()}
    # A capitalized word that the documents also write in lower case is a common word at a sentence start.
    lower_words: set[str] = {
        match.group(0)
        for document in game.documents
        for match in WORD_PATTERN.finditer(document.text)
        if match.group(0).islower()
    }
    word_counts: list[int] = sorted({len(name.split()) for name in comparable})
    findings: list[Finding] = []
    for document in game.documents:
        reported: set[str] = set()
        for run in capitalized_runs(document.text):
            for count in word_counts:
                for start in range(len(run) - count + 1):
                    candidate: str = " ".join(run[start : start + count])
                    folded: str = candidate.casefold()
                    if folded in spellings or folded in reported or is_known_word(folded, name_parts, lower_words):
                        continue
                    closest: str | None = closest_name(folded, comparable)
                    if closest is None:
                        continue
                    reported.add(folded)
                    findings.append(
                        Finding(
                            severity="warning",
                            rule="registry.near_duplicate_name",
                            message=f"The document {document.meta.id} writes '{candidate}', which is close to the "
                            f"registry name '{spellings[closest]}'.",
                            file=document.file,
                            fix_hint=f"Write the name with a reference such as `{{{{char:<id>}}}}`, or fix the "
                            f"spelling to '{spellings[closest]}'. If it is another person, add it to story.yaml.",
                        )
                    )
    return findings


def is_known_word(folded: str, name_parts: set[str], lower_words: set[str]) -> bool:
    words: list[str] = folded.split()
    return all(word in name_parts for word in words) or (len(words) == 1 and folded in lower_words)


def closest_name(folded: str, names: list[str]) -> str | None:
    words: int = len(folded.split())
    near: list[tuple[int, str]] = [
        (distance, name)
        for name in names
        if len(name.split()) == words
        for distance in [edit_distance(folded, name)]
        if 0 < distance <= allowed_distance(name)
    ]
    return min(near)[1] if near else None


def timeline_reference_findings(game: Game) -> list[Finding]:
    character_ids: set[str] = {character.id for character in game.story.characters}
    location_ids: set[str] = {location.id for location in game.story.locations}
    findings: list[Finding] = []
    for index, event in enumerate(game.story.timeline):
        findings.extend(
            Finding(
                severity="error",
                rule="registry.unknown_participant",
                message=f"The event '{event.id}' names the participant '{participant}', who is not a character.",
                file=STORY_FILE,
                path=f"timeline.{index}.participants.{position}",
                fix_hint="Use the id of a character from the characters list.",
            )
            for position, participant in enumerate(event.participants)
            if participant not in character_ids
        )
        if event.location is not None and event.location not in location_ids:
            findings.append(
                Finding(
                    severity="error",
                    rule="registry.unknown_location",
                    message=f"The event '{event.id}' happens at '{event.location}', which is not a location.",
                    file=STORY_FILE,
                    path=f"timeline.{index}.location",
                    fix_hint="Use the id of a location from the locations list, or add the location.",
                )
            )
    return findings


def overlaps(first: TimelineEvent, second: TimelineEvent) -> bool:
    """Tell if two events share a moment. Touching ends do not count: a person can leave and arrive at once."""
    first_start: datetime = first.start_time
    second_start: datetime = second.start_time
    first_end: datetime = first.end_time or first_start
    second_end: datetime = second.end_time or second_start
    if first.end is None and second.end is None:
        return first_start == second_start
    if first.end is None:
        return second_start < first_start < second_end
    if second.end is None:
        return first_start < second_start < first_end
    return max(first_start, second_start) < min(first_end, second_end)


def two_places_findings(game: Game) -> list[Finding]:
    names: dict[str, str] = {character.id: character.name for character in game.story.characters}
    timeline: list[TimelineEvent] = list(game.story.timeline)
    findings: list[Finding] = []
    for later_index, later in enumerate(timeline):
        for earlier in timeline[:later_index]:
            if later.location is None or earlier.location is None or later.location == earlier.location:
                continue
            if not overlaps(earlier, later):
                continue
            findings.extend(
                Finding(
                    severity="error",
                    rule="registry.two_places",
                    message=f"{names.get(person, person)} is at '{earlier.location}' ({earlier.id}) and at "
                    f"'{later.location}' ({later.id}) at the same time. Nobody can be in two places at once.",
                    file=STORY_FILE,
                    path=f"timeline.{later_index}",
                    fix_hint="Change the times, the location, or the participants of one of the two events.",
                )
                for person in sorted(set(earlier.participants) & set(later.participants))
            )
    return findings
