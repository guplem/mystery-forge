"""The deduction: a culprit among the suspects, a way to rule out every innocent suspect, and proofs in the documents.

A case is fair only when players can name the culprit from the evidence alone. A suspect with no exclusion clue fits
the evidence as well as the culprit does, so the accusation becomes a guess. The puzzles must matter too: when every
proof is in a plain document, players can skip the puzzles and still accuse, so the proofs must cite hidden clues
that only a solved puzzle reveals.
"""

from typing import Final

from mystery_forge.checks.game_index import (
    STORY_FILE,
    ClueEntry,
    clues_by_id,
    documents_by_id,
    revealed_clue_ids,
    stage_positions,
)
from mystery_forge.config import GameConfig
from mystery_forge.findings import Finding
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.spec.models import AccusationQuestion, Character, Deduction, Story

MIN_HIDDEN_CLUES: Final[int] = 2


def check_deduction(game: Game) -> list[Finding]:
    deduction: Deduction | None = game.story.deduction
    if deduction is None:
        return missing_deduction_findings(game)
    return [
        *culprit_findings(game, deduction),
        *exclusion_findings(game, deduction),
        *proof_findings(game, deduction),
        *who_question_findings(game, deduction),
        *puzzle_proof_findings(game, deduction),
        *elimination_findings(
            game.story, {clue_id for clue_id, entry in clues_by_id(game).items() if entry.clue.hidden}
        ),
    ]


def missing_deduction_findings(game: Game) -> list[Finding]:
    if not game.flow.accusation:
        return []
    return [
        Finding(
            severity="error",
            rule="deduction.missing",
            message="flow.yaml asks for an accusation, but story.yaml has no deduction.",
            file=STORY_FILE,
            path="deduction",
            fix_hint="Add the deduction (culprit, questions, exclusions) to story.yaml, or set accusation to false.",
        )
    ]


def culprit_findings(game: Game, deduction: Deduction) -> list[Finding]:
    # The story model makes sure that the culprit is a character, so the lookup cannot fail.
    index: int = next(
        position for position, character in enumerate(game.story.characters) if character.id == deduction.culprit
    )
    culprit: Character = game.story.characters[index]
    if culprit.is_suspect:
        return []
    return [
        Finding(
            severity="error",
            rule="deduction.culprit_not_suspect",
            message=f"The culprit {culprit.name} is not a suspect, so players never consider them.",
            file=STORY_FILE,
            path=f"characters.{index}.is_suspect",
            fix_hint="Set is_suspect to true for the culprit.",
        )
    ]


def exclusion_findings(game: Game, deduction: Deduction) -> list[Finding]:
    characters: dict[str, Character] = {character.id: character for character in game.story.characters}
    findings: list[Finding] = []
    for index, exclusion in enumerate(deduction.exclusions):
        if exclusion.suspect not in characters:
            findings.append(
                Finding(
                    severity="error",
                    rule="deduction.unknown_suspect",
                    message=f"The exclusion names '{exclusion.suspect}', who is not a character.",
                    file=STORY_FILE,
                    path=f"deduction.exclusions.{index}.suspect",
                    fix_hint="Use the id of a suspect from the characters list.",
                )
            )
        elif exclusion.suspect == deduction.culprit:
            findings.append(
                Finding(
                    severity="error",
                    rule="deduction.excludes_culprit",
                    message=f"The exclusion rules out the culprit {characters[exclusion.suspect].name}.",
                    file=STORY_FILE,
                    path=f"deduction.exclusions.{index}.suspect",
                    fix_hint="Remove this exclusion. Only innocent suspects get one.",
                )
            )
    excluded: set[str] = {exclusion.suspect for exclusion in deduction.exclusions}
    findings.extend(
        Finding(
            severity="error",
            rule="deduction.suspect_not_excluded",
            message=f"No exclusion rules out {character.name}, so players cannot rule out {character.name}.",
            file=STORY_FILE,
            path="deduction.exclusions",
            fix_hint=f"Add an exclusion for '{character.id}' with a clue that clears them, such as an alibi.",
        )
        for character in game.story.characters
        if character.is_suspect and character.id != deduction.culprit and character.id not in excluded
    )
    return findings


def proof_findings(game: Game, deduction: Deduction) -> list[Finding]:
    """Report proof clues whose document players never get. The ledger check reports unknown clue ids."""
    citations: list[tuple[str, list[str]]] = [
        (f"deduction.questions.{index}.proven_by", question.proven_by)
        for index, question in enumerate(deduction.questions)
    ]
    citations.extend(
        (f"deduction.exclusions.{index}.clues", exclusion.clues) for index, exclusion in enumerate(deduction.exclusions)
    )
    clues: dict[str, ClueEntry] = clues_by_id(game)
    documents: dict[str, AssembledDocument] = documents_by_id(game)
    positions: dict[str, int] = stage_positions(game)
    findings: list[Finding] = []
    for path, clue_ids in citations:
        for position, clue_id in enumerate(clue_ids):
            entry: ClueEntry | None = clues.get(clue_id)
            # A hidden clue is in no document: the ledger checks that a puzzle reveals it.
            if entry is None or entry.clue.document is None:
                continue
            document: AssembledDocument | None = documents.get(entry.clue.document)
            if document is not None and document.meta.stage in positions:
                continue
            findings.append(
                Finding(
                    severity="error",
                    rule="deduction.proof_unavailable",
                    message=f"The proof clue '{clue_id}' is in {entry.clue.document}, which is in no envelope that "
                    "players open.",
                    file=STORY_FILE,
                    path=f"{path}.{position}",
                    fix_hint="Cite a clue from a document of a stage in flow.yaml, or fix the document's stage.",
                )
            )
    return findings


def covers_suspect(question: AccusationQuestion, suspect: Character) -> bool:
    names: list[str] = [name.casefold() for name in (suspect.name, *suspect.aliases)]
    id_parts: set[str] = {suspect.id, *suspect.id.split("-")}
    return any(
        option.id in id_parts or any(name in option.text.casefold() for name in names) for option in question.options
    )


def who_question_findings(game: Game, deduction: Deduction) -> list[Finding]:
    suspects: list[Character] = [character for character in game.story.characters if character.is_suspect]
    if not suspects:
        return []
    if any(all(covers_suspect(question, suspect) for suspect in suspects) for question in deduction.questions):
        return []
    return [
        Finding(
            severity="warning",
            rule="deduction.no_who_question",
            message="No accusation question offers one option for each suspect, so players may never name the culprit.",
            file=STORY_FILE,
            path="deduction.questions",
            fix_hint="Add a question such as 'Who did it?' with one option per suspect that names the suspect.",
        )
    ]


def puzzle_proof_findings(game: Game, deduction: Deduction) -> list[Finding]:
    """Report each accusation question whose proof cites no clue that a puzzle reveals: players can answer it without
    solving anything, so its points reward reading, not puzzles."""
    revealed: set[str] = revealed_clue_ids(game)
    return [
        Finding(
            severity="error",
            rule="deduction.puzzles_not_needed",
            message=f"The accusation question '{question.id}' cites no hidden clue that a puzzle reveals, so players "
            "can answer it without solving the puzzles.",
            file=STORY_FILE,
            path=f"deduction.questions.{index}.proven_by",
            fix_hint="Add a hidden clue (hidden: true, revealed_by: <puzzle id>) whose quote states the fact that "
            "the puzzle reveals, and cite it in proven_by of the question.",
        )
        for index, question in enumerate(deduction.questions)
        if not revealed.intersection(question.proven_by)
    ]


def elimination_findings(story: Story, hidden_ids: set[str] | None = None) -> list[Finding]:
    """Report a culprit that players can name without a puzzle: plain clues alone clear every innocent suspect.

    `hidden_ids` holds the hidden clues of the whole game; without it, only the hidden clues of the story count.
    """
    if story.deduction is None or not story.deduction.exclusions:
        return []
    hidden: set[str] = hidden_ids if hidden_ids is not None else {clue.id for clue in story.clues if clue.hidden}
    if any(hidden.intersection(exclusion.clues) for exclusion in story.deduction.exclusions):
        return []
    return [
        Finding(
            severity="error",
            rule="deduction.culprit_by_elimination",
            message="Plain clues alone clear every innocent suspect, so players can name the culprit by elimination "
            "without solving a puzzle.",
            file=STORY_FILE,
            path="deduction.exclusions",
            fix_hint="Clear at least one innocent suspect only with a hidden clue that a puzzle reveals: cite it in "
            "that exclusion, and make sure that no plain document clears this suspect on its own.",
        )
    ]


def hidden_clue_count_findings(story: Story, config: GameConfig) -> list[Finding]:
    """Warn when a case-file story has too few hidden clues for the puzzles to carry the deduction."""
    if config.format == "envelopes":
        return []
    hidden: int = sum(1 for clue in story.clues if clue.hidden)
    if hidden >= MIN_HIDDEN_CLUES:
        return []
    return [
        Finding(
            severity="warning",
            rule="deduction.few_hidden_clues",
            message=f"The story has {hidden} hidden clues; a case needs at least {MIN_HIDDEN_CLUES}, so that the "
            "accusation needs puzzle answers.",
            file=STORY_FILE,
            path="clues",
            fix_hint="Add hidden clues (hidden: true, no document): facts in plain words that a puzzle reveals, such "
            "as a time, a place, an object, or a number. Cite them in the proofs of the accusation questions.",
        )
    ]
