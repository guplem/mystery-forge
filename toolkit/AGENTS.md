# toolkit

The Python package `mystery_forge` and its CLI `forge`. It loads configs, builds puzzle mechanics, checks games, and renders the outputs. The generator calls it as `uv run --project ../toolkit forge <verb>` from `generator/`.

## Module map

| Module                   | Concern                                                                                                                |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| `answers.py`             | Answer normalization and the salted SHA-256 hash. The JavaScript copy must match `contracts/answer-vectors.json`.      |
| `config.py`              | Load and validate a user config against `contracts/game-config.schema.json`, fill the defaults, return `GameConfig`.   |
| `brief.py`               | The numbers that drive a generation (puzzle count, stages, solvers). Must match `contracts/estimate-vectors.json`.     |
| `draw.py`                | The seeded draw of story ingredients and mechanic candidates, filtered by the config.                                  |
| `paths.py`               | The real Desktop and Downloads folders (Windows known folders, XDG), safe folder names, the newest config file.        |
| `findings.py`            | `Finding`: the one shape of every problem that the loader and the checks report.                                       |
| `text_measure.py`        | Word counts and text widths that work in every script, also in Japanese, Chinese, and Thai, which use no spaces.       |
| `yaml_loading.py`        | YAML where every scalar stays text (so `0420` keeps its zero), with the line of every value.                           |
| `i18n.py`                | The fixed output texts, dates, and weekdays: 7 checked tables, plus a translated pack per game for other languages.    |
| `catalog/`               | Package data: 91 mechanics, story ingredient decks, evidence types, the design rules for writers; typed loader.        |
| `spec/models.py`         | Pydantic models of `story.yaml`, `flow.yaml`, `puzzles/*.yaml`, and the document front matter.                         |
| `spec/loader.py`         | Read a game's `source/` folder into the models, with one finding per problem.                                          |
| `spec/documents.py`      | Document bodies: `{{kind:id}}` references, Markdown directives, and plain text.                                        |
| `mechanics/`             | One module per mechanic family. `base.py` is the interface; `registry.py` maps catalog ids to builders.                |
| `game.py`                | `Game`: the assembled, validated model that `game.json` holds.                                                         |
| `assemble.py`            | Load the source, build each puzzle, render each document body, and return `Game` plus findings.                        |
| `story_checks.py`        | Checks of `story.yaml` alone, before any puzzle exists.                                                                |
| `plan.py`                | The puzzle plan (`plan.yaml`) and its checks: ownership, graph, mechanics, variety, budget, written-game drift.        |
| `checks/`                | The whole-game checks, one module per rule family; `runner.py` runs them.                                              |
| `fix_groups.py`          | Group findings by the writer that owns their files, for parallel fixer subagents.                                      |
| `panel/`                 | Solver packets per stage, the story-only packet, the guesser packet, and the judge with the panel thresholds.          |
| `verification.py`        | Content hashes per puzzle, and the ledger that tells fresh checks from stale ones and the panel stages to run.         |
| `render/`                | HTML and PDF outputs: materials, manual, hints, solutions, companion. `game_renderer.py` is the entry point.           |
| `render/layout.py`       | Page height estimates and the split of a long text, so that toolkit-built lists flow over as many sheets as they need. |
| `render_checks.py`       | Checks of the rendered pages: the round-trip decode of each artifact, and answer leaks on a printed sheet.             |
| `export.py`              | Copy the rendered outputs to the user's output folder, with the spoilers in their own folder.                          |
| `render/internal_ids.py` | Replace internal ids (P3, D12) with printed codes and titles in hints and solutions.                                   |
| `cli.py`                 | The `forge` command line: the parser, setup, config, games, and the verbs that need no game. Every verb prints JSON.   |
| `cli_game.py`            | The `forge` verbs that work on one game folder: check, writer-tasks, material, packets, judge, status, render, export. |
| `cli_output.py`          | The output helpers of every verb: the JSON object, the capped findings, and the report files.                          |

## Conventions

- One test file per module: `tests/test_<module>.py`. Shared fixture games live in `tests/fixtures/`.
- Models are pydantic v2 classes with explicit field types. Load agent-written YAML with `yaml_loading.py`, never with `yaml.safe_load`. The catalog files are written by developers, so `catalog/loader.py` may use `yaml.safe_load`.
- A function that touches the system (files, the browser, the registry) takes that dependency as a parameter, so the tests can pass a fake on every operating system.

## Gotchas

- **Coverage must reach 100% on Windows and on Linux.** Never branch on `sys.platform` inside logic; pass the platform in as a value.
- **Browser tests use the system Chrome or Edge** (`render/pdf.py`). Coverage of the Playwright code needs `concurrency = ["thread", "greenlet"]` in `pyproject.toml`; keep it.
- **Parallel fixers verify with `--only <files> --no-write`** on `forge check`, `forge assemble`, and `forge render`, so they never overwrite the shared reports. Findings with no file form one `game` group that runs alone.
