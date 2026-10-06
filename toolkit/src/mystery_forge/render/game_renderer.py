"""Render an assembled game: plan the sheets of every output, write the HTML files, and print them with a browser.

Without a browser, the render writes only the HTML files. With one, it also writes the PDF files and the preview
images, and the report carries what the checks need from the DOM: the overflow findings, the visible text of each
sheet, and each artifact as the browser drew it (for the round-trip decode of `adr/0004-verification-strategy.md`).
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.mechanics.base import RenderedArtifact
from mystery_forge.render.hints import hint_sheets
from mystery_forge.render.html import render_output_html
from mystery_forge.render.manual import manual_sheets
from mystery_forge.render.materials import DocumentPage, materials_sheets
from mystery_forge.render.pdf import SheetBrowser, overflow_findings, rendered_artifacts
from mystery_forge.render.sheets import OutputId, OutputPlan, number_sheets, number_sheets_by_stage
from mystery_forge.render.solutions import solution_sheets
from mystery_forge.render.themes import StyleSettings, style_settings
from mystery_forge.spec.models import VisualStyle

PREVIEW_FOLDER: str = "previews"


class RenderedOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: OutputId
    html_file: Path
    pdf_file: Path | None
    sheet_count: int
    # The role of each sheet ("register", "document", ...), so a check can tell the answer register apart.
    sheet_roles: list[str]
    # The stage whose envelope holds each sheet, or None for the pages outside the envelopes.
    sheet_stages: list[str | None]
    # The visible text of each sheet, read from the DOM. Empty without a browser.
    sheet_texts: list[str]


class RenderReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    theme: VisualStyle
    files: list[Path]
    outputs: dict[OutputId, RenderedOutput]
    findings: list[Finding]
    # Each artifact as the browser drew it, by puzzle id. Empty without a browser.
    artifacts: dict[str, RenderedArtifact]
    previews: list[Path]


def output_plans(game: Game) -> list[OutputPlan]:
    """Plan every output. The manual comes first and lists the page count of the others."""
    others: list[OutputPlan] = [OutputPlan(id="materials", sheets=number_sheets_by_stage(materials_sheets(game)))]
    if game.config.assistance.hints:
        others.append(OutputPlan(id="hints", sheets=number_sheets(hint_sheets(game))))
    others.append(OutputPlan(id="solutions", sheets=number_sheets(solution_sheets(game))))
    counts: dict[OutputId, int] = {plan.id: len(plan.sheets) for plan in others}
    return [OutputPlan(id="manual", sheets=number_sheets(manual_sheets(game, counts))), *others]


def sheet_source_files(game: Game, plan: OutputPlan) -> list[str | None]:
    """The source file that each sheet shows, so an overflow finding points to the document to shorten."""
    files: dict[str, str] = {document.meta.id: document.file for document in game.documents}
    return [
        files.get(sheet.content.document_id) if isinstance(sheet.content, DocumentPage) else None
        for sheet in plan.sheets
    ]


def render_game(
    game: Game, out_dir: Path, browser: SheetBrowser | None, theme_override: VisualStyle | None = None
) -> RenderReport:
    """Write every output of the game into `out_dir`. `theme_override` replaces the theme that the config picks."""
    settings: StyleSettings = style_settings(game, theme_override)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    previews: list[Path] = []
    findings: list[Finding] = []
    artifacts: dict[str, RenderedArtifact] = {}
    outputs: dict[OutputId, RenderedOutput] = {}
    for plan in output_plans(game):
        html: str = render_output_html(plan, settings, game.story.title, game.config.language)
        html_path: Path = out_dir / plan.files.html
        html_path.write_text(html, encoding="utf-8")
        files.append(html_path)
        pdf_path: Path | None = None
        texts: list[str] = []
        if browser is not None:
            pdf_path = out_dir / plan.files.pdf
            preview_paths: list[Path] = [
                out_dir / PREVIEW_FOLDER / f"{plan.id}-{index}.png" for index in range(1, len(plan.sheets) + 1)
            ]
            (out_dir / PREVIEW_FOLDER).mkdir(exist_ok=True)
            probe = browser.print_output(html, pdf_path, preview_paths)
            files.append(pdf_path)
            previews.extend(preview_paths)
            texts = [sheet.text for sheet in probe.sheets]
            findings.extend(overflow_findings(probe, plan.files.html, sheet_source_files(game, plan)))
            if plan.id == "materials":
                artifacts = rendered_artifacts(probe)
        outputs[plan.id] = RenderedOutput(
            id=plan.id,
            html_file=html_path,
            pdf_file=pdf_path,
            sheet_count=len(plan.sheets),
            sheet_roles=[sheet.role for sheet in plan.sheets],
            sheet_stages=[sheet.stage for sheet in plan.sheets],
            sheet_texts=texts,
        )
    return RenderReport(
        theme=settings.theme.id,
        files=files,
        outputs=outputs,
        findings=findings,
        artifacts=artifacts,
        previews=previews,
    )
