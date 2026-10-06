# Rendering stack: Jinja templates, fixed sheets, and Playwright

## Context

The outputs are print PDFs and one offline HTML companion file. Both must look good in color, grayscale, and low-ink mode, on A4 and Letter. The companion must work from `file://` on any computer, and Chrome blocks `@font-face` URLs on `file://` pages.

## Decision

- Jinja2 templates (with `StrictUndefined`, so a missing value fails) render one HTML file per output. Each document kind has one template; each theme is a set of CSS variables and fonts.
- Every printed page is a fixed-size `.sheet` element with `break-after: page`. The layout never relies on the browser's automatic page flow. A long document gets explicit page-break directives.
- The bundled fonts are open-license (OFL or Apache) files, inlined as base64 data URLs, so the HTML is one self-contained file.
- Playwright (Python) prints the PDFs with the installed Chrome, then Edge, then Playwright's own Chromium. It never downloads a browser on its own; `forge doctor --install-browser` does that on request.
- Before the PDF export, a probe in the page reports every sheet whose content overflows, and the checks read the text of each sheet from the DOM. The checks never read text back from the PDF, because ligatures, rotated text, and letter grids extract badly.
- The companion page checks answers against salted SHA-256 hashes with a pure-JavaScript SHA-256, because `crypto.subtle` is not available in every `file://` context.

## Consequences

- Rendering needs a Chromium-based browser; `forge doctor` reports one that is missing.
- Template changes are tested by rendering every document kind from fixtures and by asserting sheet counts, overflow, and text, never by pixel comparison.
