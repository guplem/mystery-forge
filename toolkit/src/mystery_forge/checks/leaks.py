"""Answer leaks: a code-like answer must not be readable in any text that players see before they solve the puzzle.

Texts are compared squashed (lowercase letters and digits only), so "B O A T", "b-o-a-t", and "taob" (reversed) all
count. A puzzle's `leak_allowlist` cuts out the passages that contain the answer on purpose. A hidden clue leaks the
same way: when a document that players hold before the revealing puzzle states its fact, the puzzle is not needed.
The music suggestions print in the manual, which players read first, so they count before every puzzle. They must also
not name the culprit.
"""

import re
from dataclasses import dataclass
from typing import Final

from mystery_forge.checks.game_index import (
    CODE_LIKE_KINDS,
    FLOW_FILE,
    MIN_SEARCH_LENGTH,
    STORY_FILE,
    ClueEntry,
    clue_entries,
    puzzles_by_id,
    squash,
    stage_positions,
)
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledPuzzle, Game
from mystery_forge.spec.loader import MUSIC_FILE
from mystery_forge.spec.models import Character, MusicSuggestion

# Replaces an allowlisted passage. A non-alphanumeric mark keeps the text on both sides from joining into a new match.
CUT_MARK: Final[str] = "|"
MUSIC_LEAK_RULE: Final[str] = "leaks.answer_in_music"
WORD_PATTERN: Final[re.Pattern[str]] = re.compile(r"\w+")
# A straight or a curly apostrophe.
POSSESSIVE_PATTERN: Final[re.Pattern[str]] = re.compile(r"['\u2019]s\b", re.IGNORECASE)
APOSTROPHE_PATTERN: Final[re.Pattern[str]] = re.compile(r"['\u2019]")
# Honorifics and name particles, squashed. They occur in ordinary titles ("Dr. Who", "La Bamba"), so they are no name
# part of the culprit.
NAME_STOP_WORDS: Final[frozenset[str]] = frozenset(
    {
        *("dr", "mr", "mrs", "ms", "miss", "sir", "lady", "lord", "don", "dona", "senor", "senora", "sra", "sr"),
        *("mme", "mlle", "herr", "frau", "prof", "capt", "captain", "inspector"),
        *("de", "del", "della", "la", "le", "las", "los", "van", "von", "der", "di", "da", "du", "dos", "das"),
    }
)


@dataclass(frozen=True)
class VisibleText:
    """A text that players can read before they solve a puzzle, with where it lives and the rule for a leak in it."""

    text: str
    label: str
    file: str
    path: str | None
    rule: str


def check_leaks(game: Game) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    findings: list[Finding] = []
    for puzzle in game.puzzles:
        position: int | None = positions.get(puzzle.source.stage)
        if position is None or puzzle.source.answer_format.kind not in CODE_LIKE_KINDS:
            continue
        findings.extend(puzzle_leak_findings(puzzle, visible_texts(game, puzzle, position)))
    return [*findings, *hidden_clue_leak_findings(game), *culprit_music_findings(game)]


def visible_texts(game: Game, puzzle: AssembledPuzzle, position: int) -> list[VisibleText]:
    """Collect the texts that players can read up to the puzzle's stage, without the puzzle's own artifact text."""
    in_text: str = "leaks.answer_in_text"
    in_title: str = "leaks.answer_in_title"
    texts: list[VisibleText] = [VisibleText(game.story.intro, "the intro", STORY_FILE, "intro", in_text)]
    texts.extend(
        VisibleText(
            stage.opening_text,
            f"the opening text of stage {stage.id}",
            FLOW_FILE,
            f"stages.{index}.opening_text",
            in_text,
        )
        for index, stage in enumerate(game.flow.stages[: position + 1])
        if stage.opening_text
    )
    positions: dict[str, int] = stage_positions(game)
    own_solver_text: str = puzzle.artifact.solver_text if puzzle.artifact is not None else ""
    for document in game.documents:
        if positions.get(document.meta.stage, position + 1) > position:
            continue
        name: str = document.meta.id
        body: str = document.text.replace(own_solver_text, "") if own_solver_text else document.text
        texts.append(VisibleText(body, f"the text of {name}", document.file, None, in_text))
        texts.append(VisibleText(document.meta.title, f"the title of {name}", document.file, "title", in_title))
        texts.extend(
            VisibleText(value, f"the field '{key}' of {name}", document.file, f"fields.{key}", in_title)
            for key, value in document.meta.fields.items()
        )
    texts.append(VisibleText(puzzle.source.title, f"the title of {puzzle.source.id}", puzzle.file, "title", in_title))
    texts.extend(
        VisibleText(value, f"the music suggestions ({field_path})", MUSIC_FILE, field_path, MUSIC_LEAK_RULE)
        for field_path, value in music_fields(game)
    )
    return texts


def music_fields(game: Game) -> list[tuple[str, str]]:
    """Each title and artist of the music suggestions, with its field path in music.yaml."""
    suggestions: list[MusicSuggestion] = game.music.suggestions if game.music is not None else []
    return [
        (f"suggestions.{index}.{name}", value)
        for index, suggestion in enumerate(suggestions)
        for name, value in (("title", suggestion.title), ("artist", suggestion.artist))
    ]


def puzzle_leak_findings(puzzle: AssembledPuzzle, texts: list[VisibleText]) -> list[Finding]:
    findings: list[Finding] = []
    main_answer: str = puzzle.accepted_normalized[0]
    if len(main_answer) < MIN_SEARCH_LENGTH:
        findings.append(
            Finding(
                severity="warning",
                rule="leaks.short_answer",
                message=f"The answer of {puzzle.source.id} has fewer than {MIN_SEARCH_LENGTH} letters or digits, so "
                "the leak check cannot search for it.",
                file=puzzle.file,
                path="answer",
                fix_hint="Read the documents of this stage and the earlier ones, and make sure no text gives the "
                "answer away.",
            )
        )
    answers: list[str] = [answer for answer in puzzle.accepted_normalized if len(answer) >= MIN_SEARCH_LENGTH]
    allowed: list[str] = [squash(entry.text) for entry in puzzle.source.leak_allowlist]
    used: set[int] = set()
    for visible in texts:
        squashed: str = squash(visible.text)
        # An allowlist entry allows a passage of a puzzle's own documents, never a music suggestion: a real title
        # that holds the answer must go, and the fixer of music.yaml cannot edit the puzzle file.
        for index, passage in enumerate(allowed if visible.rule != MUSIC_LEAK_RULE else []):
            if passage and passage in squashed:
                used.add(index)
                squashed = squashed.replace(passage, CUT_MARK)
        findings.extend(
            leak_finding(puzzle, visible, answer, reversed_form)
            for answer in answers
            for reversed_form in (False, True)
            if (answer[::-1] if reversed_form else answer) in squashed
            and not (reversed_form and answer == answer[::-1])
        )
    findings.extend(
        Finding(
            severity="warning",
            rule="leaks.allowlist_unused",
            message=f"The allowed leak text '{entry.text}' of {puzzle.source.id} appears in no text that players see "
            "before the puzzle.",
            file=puzzle.file,
            path=f"leak_allowlist.{index}.text",
            fix_hint="Copy the passage word for word from the document, or remove the entry.",
        )
        for index, entry in enumerate(puzzle.source.leak_allowlist)
        if index not in used
    )
    return findings


def leak_finding(puzzle: AssembledPuzzle, visible: VisibleText, answer: str, reversed_form: bool) -> Finding:
    how: str = "reversed " if reversed_form else ""
    fix_hint: str = (
        "Replace this music suggestion with another real work that fits the story."
        if visible.rule == MUSIC_LEAK_RULE
        else f"Rephrase the text so that it does not contain the answer. If the text must contain it, add the "
        f"passage to `leak_allowlist` in {puzzle.file} with the reason."
    )
    return Finding(
        severity="error",
        rule=visible.rule,
        message=f"The answer of {puzzle.source.id} ('{answer}') appears {how}in {visible.label} ({visible.file}), "
        "which players read before they solve it.",
        # A leak in a document body goes to the puzzle's owner, who can fix it either way: change the answer, or
        # allow the passage in the puzzle file. The writer of another puzzle's document cannot edit that allowlist.
        file=puzzle.file if visible.path is None else visible.file,
        path="leak_allowlist" if visible.path is None else visible.path,
        fix_hint=fix_hint,
    )


def hidden_clue_leak_findings(game: Game) -> list[Finding]:
    positions: dict[str, int] = stage_positions(game)
    puzzles: dict[str, AssembledPuzzle] = puzzles_by_id(game)
    findings: list[Finding] = []
    for entry in clue_entries(game):
        revealer: AssembledPuzzle | None = puzzles.get(entry.clue.revealed_by or "")
        position: int | None = positions.get(revealer.source.stage) if revealer is not None else None
        if not entry.clue.hidden or revealer is None or position is None:
            continue
        fact: str = squash(entry.clue.quote)
        findings.extend(
            hidden_clue_leak_finding(entry, revealer, f"The text of {document.meta.id}", document.file)
            for document in game.documents
            if positions.get(document.meta.stage, position + 1) <= position and fact in squash(document.text)
        )
        findings.extend(
            hidden_clue_leak_finding(entry, revealer, "A music suggestion", MUSIC_FILE, field_path)
            for field_path, value in music_fields(game)
            if fact in squash(value)
        )
    return findings


def hidden_clue_leak_finding(
    entry: ClueEntry, revealer: AssembledPuzzle, where: str, file: str, path: str | None = None
) -> Finding:
    return Finding(
        severity="warning",
        rule="leaks.hidden_clue_in_text",
        message=f"{where} states the hidden clue '{entry.clue.id}' word for word, and players read it before they "
        f"solve {revealer.source.id}, the puzzle that reveals it.",
        file=file,
        path=path,
        fix_hint=f"Remove the fact from the text, so that only {revealer.source.id} reveals it. In a document, you "
        "may instead turn the clue into a plain clue of that document.",
    )


def culprit_music_findings(game: Game) -> list[Finding]:
    """Find a music suggestion that shares a whole name word with the culprit, such as "Felix" for Felix Ward."""
    culprit: Character | None = next((character for character in game.story.characters if character.is_culprit), None)
    if culprit is None:
        return []
    # Each capitalized word of the name counts alone, also a short one such as "Li": the match is whole-word, so chance
    # hits are rare. A lowercase word such as "bin" in "Ali bin Omar" is a particle that the stop list may not hold.
    # An alias such as "The Fox" counts only as a whole phrase, because its "The" alone would match any title. An
    # alias with no letters, such as "?", gives no phrase, and an empty phrase would match every title.
    names: list[tuple[str, ...]] = [
        (squash(word),)
        for word in name_words(culprit.name)
        if len(word) > 1 and not word[0].islower() and squash(word) not in NAME_STOP_WORDS
    ]
    names.extend(phrase for alias in culprit.aliases if (phrase := tuple(map(squash, name_words(alias)))))
    return [
        Finding(
            severity="error",
            rule="leaks.culprit_in_music",
            # The message names no one: the person who runs the generator may play the game.
            message=f"The music suggestions ({field_path}) share a name with the culprit, and players read the "
            "manual before they play.",
            file=MUSIC_FILE,
            path=field_path,
            fix_hint="Replace this music suggestion with another real work that fits the story and shares no name "
            "with any character.",
        )
        for field_path, value in music_fields(game)
        if any(contains_phrase(tuple(map(squash, name_words(value))), name) for name in names)
    ]


def name_words(text: str) -> list[str]:
    """Split a name or a title into words, without a possessive "'s": "Felix's Theme" gives "Felix" and "Theme".

    Every other apostrophe joins its word: "Don't" gives "Dont", not the name "Don", and "O'Brien" gives "OBrien".
    """
    return WORD_PATTERN.findall(APOSTROPHE_PATTERN.sub("", POSSESSIVE_PATTERN.sub("", text)))


def contains_phrase(words: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    return any(words[start : start + len(phrase)] == phrase for start in range(len(words) - len(phrase) + 1))
