# Testing strategy

## Context

Agents build and change this project with no human review. The tests are the review. The project mixes pure logic, browser glue, a browser renderer, and an LLM workflow, and each needs a different kind of test.

## Decision

- **Unit tests, test-first, 100% gate.** The toolkit fails below 100% of lines and branches (`pytest --cov`). The configurator logic files and the companion logic fail below 100% of lines, branches, and functions (`node --test` coverage thresholds).
- **Contract vectors.** Every file in `contracts/` has vectors that both the Python and the JavaScript tests run.
- **Fixture games.** `toolkit/tests/fixtures/` holds hand-written games. The golden game must assemble, pass every check, and render. Each fault game plants one bug (a misspelled name, a leaked answer, a hint that cites the wrong document, a second valid answer), and the matching check must catch it.
- **Browser tests** (pytest marker `browser`) render real PDFs with the system Chrome or Edge and open the configurator from `file://` in Chromium and Firefox. They assert sheet counts, overflow, and text, never pixels.
- **Skill tests.** Each path through a pskill skill graph has a `tests/<case>.yaml` case with recorded answers. `pskill test` replays them with no model.
- **Live runs** of `claude -p` in `generator/` generate real games from the example configs. They are slow and cost tokens, so they run by hand, not in CI.

## Consequences

- `configurator/app.js` (DOM glue) is excluded from the unit coverage and covered by the browser tests. Keep it thin.
- A browser test that cannot find a browser fails; it never skips silently in CI.
