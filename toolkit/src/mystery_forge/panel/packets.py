"""Player packets: the text that a solver subagent gets for one stage, and the text that the guesser gets.

A solver must see what a player sees at that stage and nothing more. A packet therefore holds the documents, the
answers of earlier stages, and the answer formats, and never the answers of its own stage, hints, solutions, mechanic
names, difficulties, or canaries. The workflow pastes the packet text into the solver prompt, so the solver needs no
file.
"""

import hashlib

from pydantic import BaseModel, ConfigDict

from mystery_forge.game import AssembledDocument, AssembledPuzzle, Game
from mystery_forge.i18n import text
from mystery_forge.render.kinds import document_kind
from mystery_forge.spec.models import AnswerFormat, Deduction

SOLVER_INSTRUCTIONS: str = """You are a player of a printed mystery game. Everything you have is below: the case, \
the documents of every envelope that you opened, and the answers that you already found. Do not open any file and do \
not search anywhere else. Use only this text.

Solve each puzzle under "Puzzles to solve now". For each puzzle:
- Give your answer in the answer format.
- Quote the exact words of the documents that prove your answer, and name the title of each document.
- List every other answer that you considered, and say which clue rules it out.
- If you cannot find an answer that the documents prove, say that you are stuck. Do not guess."""

GUESSER_INSTRUCTIONS: str = """You are a player of a printed mystery game, but you have no documents. You know only \
the case summary below and the answer format of each puzzle. Give your best guess for each puzzle code."""

ACCUSATION_INSTRUCTIONS: str = "Answer each question with the id of one option, and quote the evidence."


class StagePacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: str
    # The codes of the puzzles of this stage, in the order of the packet.
    codes: list[str]
    # The ids of the accusation questions; only the last stage has them.
    questions: list[str]
    text: str
    sha256: str


class GuesserPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    codes: list[str]
    text: str
    sha256: str


def build_stage_packets(game: Game) -> list[StagePacket]:
    """Return one packet per stage, in flow order."""
    last_stage: str = game.flow.stages[-1].id
    return [
        stage_packet(game, stage.id, game.story.deduction if stage.id == last_stage else None)
        for stage in game.flow.stages
    ]


def stage_packet(game: Game, stage: str, deduction: Deduction | None) -> StagePacket:
    earlier: list[AssembledPuzzle] = [
        puzzle for puzzle in ordered_puzzles(game) if stage_index(game, puzzle.source.stage) < stage_index(game, stage)
    ]
    current: list[AssembledPuzzle] = [puzzle for puzzle in ordered_puzzles(game) if puzzle.source.stage == stage]
    sections: list[str] = [
        f"# {game.story.title}\n\n{SOLVER_INSTRUCTIONS}",
        f"# The case\n\n{game.story.intro}",
        *opened_envelopes_section(game, stage),
        "# Documents",
        *(document_section(document) for document in available_documents(game, stage)),
        answers_found_section(earlier),
        "# Puzzles to solve now\n\n" + "\n".join(puzzle_entry(game, puzzle) for puzzle in current),
    ]
    if deduction is not None:
        sections.append(accusation_section(deduction))
    packet_text: str = "\n\n".join(sections) + "\n"
    return StagePacket(
        stage=stage,
        codes=[puzzle.code for puzzle in current],
        questions=[question.id for question in deduction.questions] if deduction is not None else [],
        text=packet_text,
        sha256=sha256_text(packet_text),
    )


def build_guesser_packet(game: Game) -> GuesserPacket:
    puzzles: list[AssembledPuzzle] = ordered_puzzles(game)
    lines: list[str] = [f"- {puzzle.code}: {format_label(puzzle.source.answer_format)}" for puzzle in puzzles]
    sections: list[str] = [
        f"# {game.story.title}\n\n{GUESSER_INSTRUCTIONS}",
        f"# The case\n\n{game.story.tagline}\n\n{game.story.premise}",
        "# Puzzles\n\n" + "\n".join(lines),
    ]
    packet_text: str = "\n\n".join(sections) + "\n"
    return GuesserPacket(codes=[puzzle.code for puzzle in puzzles], text=packet_text, sha256=sha256_text(packet_text))


def canaries(game: Game) -> dict[str, str]:
    return {puzzle.code: puzzle.source.canary for puzzle in game.puzzles}


def stage_index(game: Game, stage: str) -> int:
    """Return the flow position of a stage. A stage that the flow lacks comes last: the checks report it."""
    ids: list[str] = [flow_stage.id for flow_stage in game.flow.stages]
    return ids.index(stage) if stage in ids else len(ids)


def ordered_puzzles(game: Game) -> list[AssembledPuzzle]:
    return sorted(game.puzzles, key=lambda puzzle: (stage_index(game, puzzle.source.stage), int(puzzle.code[1:])))


def available_documents(game: Game, stage: str) -> list[AssembledDocument]:
    """Return the documents that players hold once they open `stage`: its own and those of every earlier stage."""
    limit: int = stage_index(game, stage)
    documents: list[AssembledDocument] = [
        document for document in game.documents if stage_index(game, document.meta.stage) <= limit
    ]
    return sorted(
        documents,
        key=lambda document: (stage_index(game, document.meta.stage), document.meta.order, int(document.meta.id[1:])),
    )


def opened_envelopes_section(game: Game, stage: str) -> list[str]:
    lines: list[str] = [
        f"- {text(game.config.language, 'envelope_label', stage=flow_stage.id)}: {flow_stage.opening_text}"
        for flow_stage in game.flow.stages[: stage_index(game, stage) + 1]
        if flow_stage.opening_text
    ]
    return ["# Envelopes you opened\n\n" + "\n".join(lines)] if lines else []


def document_section(document: AssembledDocument) -> str:
    """The document as players hold it: the title, the printed header fields (sender, date, subject), and the text."""
    heading: str = f"## {document.meta.title} ({document_kind(document.meta.kind).name})"
    fields: str = "".join(f"{key}: {value}\n" for key, value in document.meta.fields.items())
    return f"{heading}\n\n{fields}\n{document.text}" if fields else f"{heading}\n\n{document.text}"


def answers_found_section(earlier: list[AssembledPuzzle]) -> str:
    lines: list[str] = [f"- {puzzle.code}: {puzzle.source.answer}" for puzzle in earlier]
    return "# Answers you already found\n\n" + ("\n".join(lines) if lines else "None yet.")


def puzzle_entry(game: Game, puzzle: AssembledPuzzle) -> str:
    titles: list[str] = [document.meta.title for document in game.documents if document.meta.puzzle == puzzle.source.id]
    lines: list[str] = [
        f"- {puzzle.code}: {puzzle.source.title}",
        f"  Answer format: {format_label(puzzle.source.answer_format)}",
    ]
    if puzzle.source.answer_format.choices:
        lines.append("  Choices: " + " | ".join(puzzle.source.answer_format.choices))
    lines.append("  Documents for this puzzle: " + ("; ".join(titles) if titles else "none"))
    return "\n".join(lines)


def format_label(answer_format: AnswerFormat) -> str:
    if answer_format.length is None:
        return answer_format.label
    return f"{answer_format.label} ({answer_format.length} characters)"


def accusation_section(deduction: Deduction) -> str:
    lines: list[str] = []
    for question in deduction.questions:
        lines.append(f"- {question.id}: {question.prompt}")
        lines.extend(f"  - {option.id}: {option.text}" for option in question.options)
    return f"# Final accusation\n\n{ACCUSATION_INSTRUCTIONS}\n\n" + "\n".join(lines)


def sha256_text(packet_text: str) -> str:
    return hashlib.sha256(packet_text.encode()).hexdigest()
