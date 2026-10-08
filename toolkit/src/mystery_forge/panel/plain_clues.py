"""The plain clue test: the story-only test of the solver panel, run on the story alone, before any document exists.

The solver panel tests whether players can skip the puzzles only after every document is written, and a fixer can then
only edit documents. When the story itself lets its plain clues prove an accusation answer, the real fix is a story
change. So right after the story review, fresh solvers get the case, the people, every plain clue quote, and the
accusation questions, and no hidden clue. The story-only judge of the panel then decides each question.
"""

from typing import Final

from mystery_forge.checks.ledger import normalize_quote_text
from mystery_forge.panel.judge import ValidSolver, judge_story_only, question_attempt
from mystery_forge.panel.models import ItemVerdict, SolverResult
from mystery_forge.panel.packets import STORY_ONLY_STAGE, StagePacket, accusation_section, sha256_text
from mystery_forge.spec.models import Clue, Deduction, Story

PLAIN_CLUE_SOLVERS: Final[int] = 3
PLAIN_CLUE_INSTRUCTIONS: Final[str] = """You are a player of a printed mystery game who skips every puzzle. The \
documents of the game are not printed yet, but below is every sentence of evidence that they will print, under the id \
of its document. You know no puzzle answer. Everything you have is below. Do not open any file and do not search \
anywhere else. Use only this text.

For each question of the final accusation, give your best answer from these sentences:
- Give the option id, and quote the exact sentences that support it, with the id of their document.
- Reasoning by elimination is fine: rule out the other options with quoted evidence.
- Leave the option empty only when the sentences give you no reason at all to prefer one option."""


def build_plain_clue_packet(story: Story) -> StagePacket | None:
    """The packet of the plain clue test, or None when the story has no accusation."""
    deduction: Deduction | None = story.deduction
    if deduction is None:
        return None
    people: list[str] = [
        f"- {character.name} ({character.role}): {character.description}" for character in story.characters
    ]
    sections: list[str] = [
        f"# {story.title}\n\n{PLAIN_CLUE_INSTRUCTIONS}",
        f"# The case\n\n{story.intro}",
        "# People\n\n" + "\n".join(people),
        "# What the documents say",
        *(document_quotes(document, clues) for document, clues in plain_clues_by_document(story).items()),
        accusation_section(deduction),
    ]
    packet_text: str = "\n\n".join(sections) + "\n"
    return StagePacket(
        stage=STORY_ONLY_STAGE,
        codes=[],
        questions=[question.id for question in deduction.questions],
        text=packet_text,
        sha256=sha256_text(packet_text),
    )


def plain_clues_by_document(story: Story) -> dict[str, list[Clue]]:
    grouped: dict[str, list[Clue]] = {}
    for clue in story.clues:
        if clue.document is not None:
            grouped.setdefault(clue.document, []).append(clue)
    return grouped


def document_quotes(document: str, clues: list[Clue]) -> str:
    return f"## Document {document}\n\n" + "\n".join(f"> {clue.quote}" for clue in clues)


def judge_plain_clue_test(story: Story, packet: StagePacket, results: list[SolverResult]) -> list[ItemVerdict]:
    """One verdict per accusation question: puzzles_not_needed when the plain clues alone prove it."""
    if story.deduction is None:
        return []
    comparable: str = normalize_quote_text(packet.text)
    valid: list[ValidSolver] = [
        ValidSolver(result=result, packet=packet, comparable_packet=comparable)
        for result in results
        if result.status == "done"
    ]
    return [
        judge_story_only(question.id, [question_attempt(solver, question) for solver in valid])
        for question in story.deduction.questions
    ]
