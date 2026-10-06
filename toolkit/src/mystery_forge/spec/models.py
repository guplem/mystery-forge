"""Pydantic models of the game source files that agents write (`adr/0003-game-source-format.md`).

These models check structure and the consistency inside one file. Rules that span files (a clue quote must appear in
its document, a puzzle must exist before a stage can open with it) live in `mystery_forge.checks`.
The loader gives these models text values; pydantic converts them to the declared types.
"""

from collections import Counter
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

RegistryId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=60)]
ClueId = RegistryId
PuzzleId = Annotated[str, StringConstraints(pattern=r"^P[1-9][0-9]?$")]
DocumentId = Annotated[str, StringConstraints(pattern=r"^D[1-9][0-9]{0,2}$")]
StageId = Annotated[str, StringConstraints(pattern=r"^[A-H]$")]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=120)]
Text = Annotated[str, StringConstraints(min_length=1)]

# An int, not Literal[1]: the loader gives text, and pydantic converts "1" to 1 only for an int field.
FormatVersion = Annotated[int, Field(ge=1, le=1)]
Difficulty = Literal["easy", "medium", "hard", "expert"]
TIME_FORMATS: tuple[str, ...] = ("%Y-%m-%d %H:%M", "%Y-%m-%d")


class SourceModel(BaseModel):
    """Base of every source model: unknown fields are errors, so a typo never disappears silently."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def find_duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def parse_story_time(value: str) -> datetime:
    for time_format in TIME_FORMATS:
        try:
            return datetime.strptime(value, time_format)
        except ValueError:
            continue
    raise ValueError(f"'{value}' is not a time in the form YYYY-MM-DD HH:MM or YYYY-MM-DD")


class Clue(SourceModel):
    """A piece of evidence: a verbatim quote from one document. Solution steps, hints, and proofs cite clues by id."""

    id: ClueId
    document: DocumentId
    quote: Text
    note: str = ""


class Character(SourceModel):
    id: RegistryId
    name: ShortText
    role: ShortText
    description: Text
    age: int | None = Field(default=None, ge=0, le=130)
    is_suspect: bool = False
    is_culprit: bool = False
    secret: str = ""
    aliases: list[ShortText] = []


class Location(SourceModel):
    id: RegistryId
    name: ShortText
    description: Text


class StoryObject(SourceModel):
    id: RegistryId
    name: ShortText
    description: Text


class TimelineEvent(SourceModel):
    """A true event of the story. The checks use the times to find people in two places at once."""

    id: RegistryId
    start: str
    end: str | None = None
    location: RegistryId | None = None
    participants: list[RegistryId] = []
    description: Text
    known_to_players: bool = False

    @property
    def start_time(self) -> datetime:
        return parse_story_time(self.start)

    @property
    def end_time(self) -> datetime | None:
        return parse_story_time(self.end) if self.end is not None else None

    @model_validator(mode="after")
    def check_times(self) -> Self:
        start: datetime = parse_story_time(self.start)
        if self.end is not None and parse_story_time(self.end) < start:
            raise ValueError(f"event '{self.id}': the end is before the start")
        return self


class AccusationOption(SourceModel):
    id: RegistryId
    text: ShortText


class AccusationQuestion(SourceModel):
    """One multiple-choice question of the final accusation, with the clues that prove the correct option."""

    id: RegistryId
    prompt: Text
    options: list[AccusationOption] = Field(min_length=2, max_length=8)
    correct: RegistryId
    points: int = Field(ge=1, le=100)
    proven_by: list[ClueId] = Field(min_length=1)

    @model_validator(mode="after")
    def check_options(self) -> Self:
        option_ids: list[str] = [option.id for option in self.options]
        duplicates: list[str] = find_duplicates(option_ids)
        if duplicates:
            raise ValueError(f"question '{self.id}': the option ids {duplicates} appear twice")
        if self.correct not in option_ids:
            raise ValueError(f"question '{self.id}': the correct option '{self.correct}' is not one of the options")
        return self


class Exclusion(SourceModel):
    """How players can rule out one innocent suspect."""

    suspect: RegistryId
    clues: list[ClueId] = Field(min_length=1)
    explanation: Text


class Deduction(SourceModel):
    culprit: RegistryId
    questions: list[AccusationQuestion] = Field(min_length=1)
    exclusions: list[Exclusion] = []


class Epilogue(SourceModel):
    """An ending. The companion and the solutions show the one with the highest `min_score_percent` reached."""

    id: RegistryId
    min_score_percent: int = Field(ge=0, le=100)
    title: ShortText
    text: Text


class RevealStep(SourceModel):
    """One step of "how you could have known": a statement plus the clues that support it."""

    text: Text
    clues: list[ClueId] = Field(min_length=1)


class Story(SourceModel):
    """The content of `story.yaml`: the fact registry, the truth, the deduction, and the framing texts."""

    format_version: FormatVersion
    title: ShortText
    tagline: Annotated[str, StringConstraints(max_length=200)]
    premise: Text
    setting: ShortText
    era: ShortText
    tone: ShortText
    truth: Text
    characters: list[Character] = Field(min_length=1)
    locations: list[Location] = []
    objects: list[StoryObject] = []
    timeline: list[TimelineEvent] = []
    clues: list[Clue] = []
    intro: Text
    deduction: Deduction | None = None
    epilogues: list[Epilogue] = Field(min_length=1)
    reveal: list[RevealStep] = []

    @model_validator(mode="after")
    def check_registry(self) -> Self:
        registry_ids: list[str] = [
            *(character.id for character in self.characters),
            *(location.id for location in self.locations),
            *(story_object.id for story_object in self.objects),
            *(event.id for event in self.timeline),
        ]
        duplicates: list[str] = find_duplicates(registry_ids)
        if duplicates:
            raise ValueError(f"the registry ids {duplicates} appear twice (characters, locations, objects, events)")
        clue_duplicates: list[str] = find_duplicates([clue.id for clue in self.clues])
        if clue_duplicates:
            raise ValueError(f"the clue ids {clue_duplicates} appear twice")
        culprits: list[str] = [character.id for character in self.characters if character.is_culprit]
        if len(culprits) > 1:
            raise ValueError(f"only one character can be the culprit, but these are: {culprits}")
        if self.deduction is not None and culprits != [self.deduction.culprit]:
            raise ValueError(
                f"deduction.culprit is '{self.deduction.culprit}', but the character marked is_culprit is {culprits}"
            )
        return self


class AnswerFormat(SourceModel):
    """What players see about the expected answer, for example "a 4-digit code"."""

    kind: Literal["word", "phrase", "number", "digits", "name", "choice"]
    label: ShortText
    length: int | None = Field(default=None, ge=1, le=60)
    choices: list[ShortText] = []


class NearMiss(SourceModel):
    """A wrong answer that players are likely to give, with a message that nudges them back."""

    answer: ShortText
    message: Text


class SolutionStep(SourceModel):
    text: Text
    uses: list[ClueId] = []


class Hint(SourceModel):
    level: int = Field(ge=1, le=3)
    text: Text
    points_to: list[ClueId] = []


class LeakAllowance(SourceModel):
    """A visible text that contains the answer on purpose, with the reason why that is fine."""

    text: ShortText
    reason: Text


class Puzzle(SourceModel):
    """The content of `puzzles/<id>.yaml`."""

    format_version: FormatVersion
    id: PuzzleId
    title: ShortText
    stage: StageId
    mechanic: RegistryId
    difficulty: Difficulty
    depends_on: list[PuzzleId] = []
    in_world_reason: Text
    reveals: Text
    answer: ShortText
    accepted: list[ShortText] = []
    near_misses: list[NearMiss] = []
    answer_format: AnswerFormat
    params: dict[str, Any] = {}
    seed: int = 0
    clues: list[Clue] = []
    solution: list[SolutionStep] = Field(min_length=1)
    hints: list[Hint] = Field(min_length=1, max_length=3)
    canary: Annotated[str, StringConstraints(min_length=6, max_length=40)]
    leak_allowlist: list[LeakAllowance] = []
    is_meta: bool = False

    @model_validator(mode="after")
    def check_puzzle(self) -> Self:
        levels: list[int] = [hint.level for hint in self.hints]
        if levels != list(range(1, len(levels) + 1)):
            raise ValueError(f"puzzle {self.id}: hint levels must be 1, 2, 3 in order, not {levels}")
        clue_duplicates: list[str] = find_duplicates([clue.id for clue in self.clues])
        if clue_duplicates:
            raise ValueError(f"puzzle {self.id}: the clue ids {clue_duplicates} appear twice")
        if self.answer_format.kind == "choice" and self.answer not in self.answer_format.choices:
            raise ValueError(f"puzzle {self.id}: the answer '{self.answer}' is not one of answer_format.choices")
        return self


class PrintOptions(SourceModel):
    cut: bool = False
    fold: bool = False
    note: str = ""


class DocumentMeta(SourceModel):
    """The front matter of `documents/<id>.md`."""

    format_version: FormatVersion
    id: DocumentId
    kind: RegistryId
    stage: StageId
    title: ShortText
    puzzle: PuzzleId | None = None
    print: PrintOptions = PrintOptions()
    # Fields that only some kinds use, such as a letter's sender or a newspaper's headline.
    fields: dict[str, str] = {}
    copies: int = Field(default=1, ge=1, le=4)
    order: int = 0


class Stage(SourceModel):
    """One envelope. Players open it at the start, or when the answer to `opens_with` tells them to."""

    id: StageId
    label: ShortText
    opens_with: Literal["start"] | PuzzleId
    opening_text: str = ""


class Flow(SourceModel):
    """The content of `flow.yaml`."""

    format_version: FormatVersion
    structure: Literal["linear", "open", "funnel"]
    stages: list[Stage] = Field(min_length=1, max_length=8)
    final_puzzle: PuzzleId | None = None
    accusation: bool = False

    @model_validator(mode="after")
    def check_stages(self) -> Self:
        duplicates: list[str] = find_duplicates([stage.id for stage in self.stages])
        if duplicates:
            raise ValueError(f"the stage ids {duplicates} appear twice")
        if self.stages[0].opens_with != "start":
            raise ValueError("the first stage must open with 'start'")
        later_starts: list[str] = [stage.id for stage in self.stages[1:] if stage.opens_with == "start"]
        if later_starts:
            raise ValueError(f"only the first stage opens with 'start', not {later_starts}")
        return self
