"""Render an assembled game: plan the sheets of every output, write the HTML files, and print them with a browser.

Without a browser, the render writes only the HTML files. With one, it also writes the PDF files and the preview
images, and the report carries what the checks need from the DOM: the overflow findings, the visible text of each
sheet, and each artifact as the browser drew it (for the round-trip decode of `adr/0004-verification-strategy.md`).
"""

import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from mystery_forge.findings import Finding
from mystery_forge.game import Game
from mystery_forge.i18n import LANGUAGES
from mystery_forge.mechanics.base import RenderedArtifact
from mystery_forge.render.hints import hint_sheets
from mystery_forge.render.html import render_output_html
from mystery_forge.render.layout import Tightness
from mystery_forge.render.manual import manual_sheets
from mystery_forge.render.materials import DocumentPage, materials_sheets
from mystery_forge.render.pdf import (
    PageProbe,
    SheetBrowser,
    overflow_findings,
    overflowing_sheets,
    rendered_artifacts,
)
from mystery_forge.render.sheets import (
    OUTPUT_HTML_FILES,
    OutputFileNames,
    OutputId,
    OutputPlan,
    number_sheets,
    number_sheets_by_stage,
    output_file_names,
)
from mystery_forge.render.solutions import solution_sheets
from mystery_forge.render.themes import StyleSettings, style_settings
from mystery_forge.spec.models import VisualStyle

PREVIEW_FOLDER: str = "previews"
# A pass prints each changed output once; most games fit in the first pass, and a few need one or two more.
MAX_PASSES: int = 5


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


def output_plans(game: Game, levels: Tightness | None = None) -> list[OutputPlan]:
    """Plan every output. The manual comes first and lists the page count of the others."""
    tight: Tightness = levels or {}
    others: list[OutputPlan] = [
        OutputPlan(id="materials", sheets=number_sheets_by_stage(materials_sheets(game, tight)))
    ]
    if game.config.assistance.hints:
        others.append(OutputPlan(id="hints", sheets=number_sheets(hint_sheets(game, tight))))
    others.append(OutputPlan(id="solutions", sheets=number_sheets(solution_sheets(game, tight))))
    counts: dict[OutputId, int] = {plan.id: len(plan.sheets) for plan in others}
    return [OutputPlan(id="manual", sheets=number_sheets(manual_sheets(game, counts, tight))), *others]


def sheet_source_files(game: Game, plan: OutputPlan) -> list[str | None]:
    """The document file that each sheet shows, or None for a sheet that the toolkit builds."""
    files: dict[str, str] = {document.meta.id: document.file for document in game.documents}
    return [
        files.get(sheet.content.document_id) if isinstance(sheet.content, DocumentPage) else None
        for sheet in plan.sheets
    ]


def groups_to_tighten(plan: OutputPlan, probe: PageProbe) -> set[str]:
    """The flow groups of the sheets that overflow. A sheet outside any flow group cannot get more room."""
    groups: set[str] = set()
    for index, _ in overflowing_sheets(probe):
        group: str | None = plan.sheets[index].group if index < len(plan.sheets) else None
        if group is not None:
            groups.add(group)
    return groups


def tightened(levels: Tightness, groups: set[str]) -> dict[str, int]:
    return {**levels, **{group: levels.get(group, 0) + 1 for group in groups}}


def preview_paths(out_dir: Path, plan: OutputPlan) -> list[Path]:
    return [out_dir / PREVIEW_FOLDER / f"{plan.id}-{index}.png" for index in range(1, len(plan.sheets) + 1)]


def remove_stale_outputs(out_dir: Path) -> None:
    """Delete the previews and the output files of an earlier render, so that a shorter render leaves no old page.

    The game language may have changed since that render, so the PDF and companion names of every language go.
    """
    shutil.rmtree(out_dir / PREVIEW_FOLDER, ignore_errors=True)
    for html_file in OUTPUT_HTML_FILES.values():
        (out_dir / html_file).unlink(missing_ok=True)
    for language in LANGUAGES:
        names: OutputFileNames = output_file_names(language)
        for name in (*names.pdfs.values(), names.companion):
            (out_dir / name).unlink(missing_ok=True)


def render_game(
    game: Game, out_dir: Path, browser: SheetBrowser | None, theme_override: VisualStyle | None = None
) -> RenderReport:
    """Write every output of the game into `out_dir`. `theme_override` replaces the theme that the config picks.

    With a browser, a sheet of a flow group that still overflows gives its group a tighter level, and the outputs
    render again, up to `MAX_PASSES` times. Only an output whose HTML changed goes back to the browser.
    """
    settings: StyleSettings = style_settings(game, theme_override)
    pdf_files: dict[OutputId, str] = output_file_names(game.config.language).pdfs
    out_dir.mkdir(parents=True, exist_ok=True)
    remove_stale_outputs(out_dir)
    levels: dict[str, int] = {}
    printed: dict[OutputId, tuple[str, PageProbe]] = {}
    pass_number: int = 0
    while True:
        pass_number += 1
        plans: list[OutputPlan] = output_plans(game, levels)
        pages: dict[OutputId, str] = {
            plan.id: render_output_html(
                plan, settings, game.story.title, game.config.language, solo=game.config.players.count == 1
            )
            for plan in plans
        }
        if browser is None:
            break
        (out_dir / PREVIEW_FOLDER).mkdir(exist_ok=True)
        groups: set[str] = set()
        for plan in plans:
            if plan.id not in printed or printed[plan.id][0] != pages[plan.id]:
                pdf_path: Path = out_dir / pdf_files[plan.id]
                probe = browser.print_output(pages[plan.id], pdf_path, preview_paths(out_dir, plan))
                printed[plan.id] = (pages[plan.id], probe)
            groups |= groups_to_tighten(plan, printed[plan.id][1])
        if not groups or pass_number >= MAX_PASSES:
            break
        levels = tightened(levels, groups)
    return written_report(game, out_dir, settings, plans, pages, {key: value[1] for key, value in printed.items()})


def written_report(
    game: Game,
    out_dir: Path,
    settings: StyleSettings,
    plans: list[OutputPlan],
    pages: dict[OutputId, str],
    probes: dict[OutputId, PageProbe],
) -> RenderReport:
    """Write the final HTML files and gather the report from the last probe of each output."""
    pdf_files: dict[OutputId, str] = output_file_names(game.config.language).pdfs
    files: list[Path] = []
    previews: list[Path] = []
    findings: list[Finding] = []
    artifacts: dict[str, RenderedArtifact] = {}
    outputs: dict[OutputId, RenderedOutput] = {}
    for plan in plans:
        html_path: Path = out_dir / plan.html_file
        html_path.write_text(pages[plan.id], encoding="utf-8")
        files.append(html_path)
        pdf_path: Path | None = None
        texts: list[str] = []
        probe: PageProbe | None = probes.get(plan.id)
        if probe is not None:
            pdf_path = out_dir / pdf_files[plan.id]
            files.append(pdf_path)
            previews.extend(preview_paths(out_dir, plan))
            texts = [sheet.text for sheet in probe.sheets]
            findings.extend(overflow_findings(probe, plan.html_file, sheet_source_files(game, plan)))
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
