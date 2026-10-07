"""The shared interface of every puzzle mechanic.

A mechanic turns a puzzle's answer and parameters into printable material (an `Artifact`). The agent chooses the
answer and the parameters; the mechanic builds the material, so the material is correct by construction. A verifier
mechanic instead checks material that the agent wrote in a document, and raises `MechanicBuildError` when the rule
does not hold.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, computed_field

from mystery_forge.answers import normalize_answer


class MechanicContext(BaseModel):
    """What a mechanic knows about the puzzle besides its own parameters."""

    model_config = ConfigDict(frozen=True)

    puzzle_id: str
    answer: str
    language: str
    seed: int
    # The resolved plain text of every document, by document id. Verifier mechanics read the material from here.
    documents: Mapping[str, str]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def normalized_answer(self) -> str:
        return normalize_answer(self.answer, self.language)


class Artifact(BaseModel):
    """The printable output of a mechanic."""

    model_config = ConfigDict(frozen=True)

    # A safe HTML fragment. The renderer wraps it in an element with `data-artifact="<puzzle id>"`.
    html: str
    # How a text-only solver perceives the material, for the solver panel packets.
    solver_text: str
    # Instructions printed next to the material, such as "Cut along the dashed lines".
    print_notes: tuple[str, ...] = ()
    # Texts that the material needs but does not print, such as a coordinate list: a document must print each one.
    needs_in_documents: tuple[str, ...] = ()


class RenderedArtifact(BaseModel):
    """The artifact as the browser rendered it: its visible text and its HTML, read from the DOM."""

    model_config = ConfigDict(frozen=True)

    text: str
    html: str


class MechanicBuildError(Exception):
    """The parameters or the answer do not allow a valid puzzle. The message says what is wrong."""

    def __init__(self, message: str, fix_hint: str) -> None:
        super().__init__(message)
        self.message: str = message
        self.fix_hint: str = fix_hint

    def __str__(self) -> str:
        return f"{self.message} (fix: {self.fix_hint})"


@dataclass(frozen=True)
class MechanicImplementation[ParamsType: BaseModel]:
    """One mechanic: its id (the catalog id), its parameter model, its builder, and its optional round-trip decoder."""

    id: str
    params_model: type[ParamsType]
    build: Callable[[ParamsType, MechanicContext], Artifact]
    # Reads the rendered artifact back and returns the answer that it encodes. The round-trip check compares the
    # normalized result with the normalized answer, which catches rendering that changed letters.
    decode_rendered: Callable[[RenderedArtifact, ParamsType, MechanicContext], str] | None = None


def parse_params[ParamsType: BaseModel](
    implementation: MechanicImplementation[ParamsType], raw_params: Mapping[str, Any]
) -> ParamsType:
    """Validate raw parameters (often text from YAML) against the mechanic's parameter model."""
    try:
        return implementation.params_model.model_validate(dict(raw_params))
    except ValidationError as error:
        problems: str = "; ".join(
            f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}" for issue in error.errors()
        )
        raise MechanicBuildError(
            f"Invalid params for mechanic '{implementation.id}': {problems}",
            fix_hint=f"Run `forge catalog show {implementation.id}` to see the parameters that this mechanic takes.",
        ) from error
