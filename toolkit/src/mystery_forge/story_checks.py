"""Checks of `story.yaml` alone, before the flow, the puzzles, and the documents exist.

The full-game checks (`mystery_forge.checks`) need an assembled game. The story step runs earlier, so this module
checks what the story can already get wrong: the timeline, the deduction structure, the clues that the deduction
cites, the endings, the audience limits, and the clichés.
"""

import re
from pathlib import Path
from typing import Final

from mystery_forge.assemble import load_config
from mystery_forge.brief import Brief
from mystery_forge.catalog.loader import load_ingredients
from mystery_forge.checks.deduction import elimination_findings, hidden_clue_count_findings
from mystery_forge.checks.runner import run_checks
from mystery_forge.config import GameConfig
from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.spec.loader import SOURCE_FOLDER, load_required_model
from mystery_forge.spec.models import Flow, Stage, Story

STORY_FILE: Final[str] = "story.yaml"
STORY_RULES: Final[tuple[str, ...]] = (
    "registry.two_places",
    "registry.unknown_location",
    "registry.unknown_participant",
    "deduction.culprit_not_suspect",
    "deduction.excludes_culprit",
    "deduction.unknown_suspect",
    "deduction.suspect_not_excluded",
    "deduction.no_who_question",
)
INTRO_WORDS: Final[tuple[int, int]] = (60, 200)
# The words that a story with no death may not use, by game language. A word that ends with "*" is a stem: it also
# matches longer words ("murder*" matches "murderer"). Any other word matches only as a whole word, so the French
# "sang" does not flag the English "sang", and "tote" does not flag "totem".
DEATH_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "en": ("murder*", "kill*", "dead", "death*", "corpse*", "blood*", "assassin*"),
    "es": ("asesin*", "muert*", "matar*", "sangre*", "cadáver*", "cadaver*"),
    "ca": ("assassin*", "mort", "morta", "morts", "mortes", "matar*", "sang", "cadàver*"),
    "fr": ("meurtr*", "tuer", "tué", "tuée", "tueur*", "mort", "morte", "morts", "sang", "cadavre*", "assassin*"),
    "de": ("mord", "mordes", "mörder*", "ermord*", "tot", "tote", "toten", "töt*", "leiche*", "blut*"),
    "it": ("omicid*", "uccid*", "uccis*", "morto", "morta", "morti", "morte", "sangue*", "cadavere*", "assassin*"),
    "pt": ("assassin*", "morto", "morta", "mortos", "morte", "matar*", "sangue*", "cadáver*"),
}


def death_pattern(language: str) -> re.Pattern[str]:
    alternatives: list[str] = [
        re.escape(word[:-1]) if word.endswith("*") else rf"{re.escape(word)}\b" for word in DEATH_WORDS[language]
    ]
    return re.compile(rf"\b(?:{'|'.join(alternatives)})", re.IGNORECASE)


def check_story_folder(game_dir: Path) -> list[Finding]:
    """Check `source/story.yaml` with the config of the game folder."""
    findings: list[Finding] = []
    story: Story | None = load_required_model(game_dir / SOURCE_FOLDER, STORY_FILE, Story, findings)
    config: GameConfig | None = load_config(game_dir, findings)
    if story is None or config is None:
        return findings
    findings.extend(structure_findings(story, config))
    findings.extend(clue_reference_findings(story))
    findings.extend(audience_findings(story, config))
    findings.extend(cliche_findings(story))
    findings.extend(
        finding.model_copy(update={"file": STORY_FILE}) for finding in hidden_clue_count_findings(story, config)
    )
    findings.extend(elimination_findings(story))
    return findings


def structure_findings(story: Story, config: GameConfig) -> list[Finding]:
    """Run the full-game rules that need only the story, on a game with no puzzle and no document."""
    placeholder_brief = Brief(
        puzzle_count=0, stage_count=1, parallel_width=1, solver_count=3, reading_words=0, printed_pages=0,
        generation_minutes=0, minutes_per_puzzle=0, seed=0, language=config.language, audience=config.audience,
        format=config.format, difficulty=config.difficulty, players=config.players.count,
    )  # fmt: skip
    placeholder_flow = Flow(format_version=1, structure="linear", stages=[Stage(id="A", label="-", opens_with="start")])
    game = Game(
        config=config, brief=placeholder_brief, story=story, flow=placeholder_flow, puzzles=[], documents=[],
        images={}, salt="",
    )  # fmt: skip
    findings: list[Finding] = [
        finding.model_copy(update={"file": STORY_FILE}) for finding in run_checks(game, only=STORY_RULES)
    ]
    if config.format != "envelopes" and story.deduction is None:
        findings.append(
            story_finding(
                "story.deduction_missing",
                "A case-file game needs a deduction: the culprit, the questions, and the exclusions.",
                "Add a `deduction` section, or ask for the envelopes format in the config.",
            )
        )
    if not any(epilogue.min_score_percent == 0 for epilogue in story.epilogues):
        findings.append(
            story_finding(
                "story.epilogue_zero",
                "No epilogue starts at 0%, so a group that fails gets no ending.",
                "Add an epilogue with min_score_percent: 0.",
            )
        )
    words: int = len(story.intro.split())
    if not INTRO_WORDS[0] <= words <= INTRO_WORDS[1]:
        findings.append(
            story_finding(
                "story.intro_length",
                f"The intro has {words} words; a read-aloud intro needs {INTRO_WORDS[0]} to {INTRO_WORDS[1]}.",
                f"Rewrite the intro to set the scene, the goal, and the stakes in {INTRO_WORDS[0]} to "
                f"{INTRO_WORDS[1]} words.",
                severity="warning",
            )
        )
    return findings


def clue_reference_findings(story: Story) -> list[Finding]:
    """Proofs, exclusions, and reveal steps cite story clues: puzzles do not exist yet, and their clues may change."""
    known: set[str] = {clue.id for clue in story.clues}
    cited: list[tuple[str, str]] = []
    if story.deduction is not None:
        cited += [
            (clue, f"question '{question.id}'") for question in story.deduction.questions for clue in question.proven_by
        ]
        cited += [
            (clue, f"exclusion of '{exclusion.suspect}'")
            for exclusion in story.deduction.exclusions
            for clue in exclusion.clues
        ]
    cited += [(clue, "a reveal step") for step in story.reveal for clue in step.clues]
    return [
        story_finding(
            "story.clue_unknown",
            f"{place} cites the clue '{clue}', which `clues` does not define.",
            "Add the clue to `clues` with its document id and its exact quote, or cite an existing clue.",
        )
        for clue, place in cited
        if clue not in known
    ]


def audience_findings(story: Story, config: GameConfig) -> list[Finding]:
    if config.audience != "kids" and config.content.death_allowed:
        return []
    texts: list[str] = [story.truth, story.intro, story.premise, *(epilogue.text for epilogue in story.epilogues)]
    texts += [event.description for event in story.timeline]
    pattern: re.Pattern[str] = death_pattern(config.language)
    match: re.Match[str] | None = next(filter(None, (pattern.search(text) for text in texts)), None)
    if match is None:
        return []
    return [
        story_finding(
            "story.audience",
            f"The story mentions death or violence ('{match.group(0)}'), but the config does not allow it.",
            "Make the mystery a theft, a disappearance, a prank, or a sabotage, with no death and no blood.",
        )
    ]


def cliche_findings(story: Story) -> list[Finding]:
    cliches = load_ingredients().cliches
    findings: list[Finding] = []
    names: list[str] = [character.name for character in story.characters]
    for cliche_name in cliches.names:
        if any(re.search(rf"\b{re.escape(cliche_name)}\b", name, re.IGNORECASE) for name in names):
            findings.append(
                story_finding(
                    "story.cliche_name",
                    f"The name '{cliche_name}' is an overused AI name.",
                    "Pick a fresh name that fits the setting and the era.",
                    severity="warning",
                )
            )
    all_text: str = " ".join([story.truth, story.intro, story.premise, story.tagline]).lower()
    for phrase in cliches.phrases:
        if phrase.lower() in all_text:
            findings.append(
                story_finding(
                    "story.cliche_phrase",
                    f"The phrase '{phrase}' is an overused AI phrase.",
                    "Say it with a concrete detail instead.",
                    severity="warning",
                )
            )
    return findings


def story_finding(rule: str, message: str, fix_hint: str, severity: str = "error") -> Finding:
    return Finding(
        severity="warning" if severity == "warning" else "error",
        rule=rule,
        message=message,
        file=STORY_FILE,
        fix_hint=fix_hint,
    )
