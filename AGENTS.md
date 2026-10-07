# mystery-forge

**Generating a game? Stop reading this file.** Open the agent in `generator/` and follow `generator/AGENTS.md` only. This file is the map for changing the project itself.

mystery-forge generates printable mystery games (envelope escape rooms and detective case files) with an AI coding agent. A static configurator page writes a config file. An agent opened in `generator/` runs the pskill skill `create-game` (pskill is a runner that gives the agent one step of a YAML workflow at a time). The agent writes the story and the puzzles as files, and the Python toolkit builds the puzzle mechanics, checks the game, and renders the PDFs and the companion page. The human view of the project (install, use, print): `README.md`.

Delegate to these agents at the right moment (each agent's own description says what it does). They fall into two groups, by when they run.

**Before you implement (explore agents, launched as preparation):**

- **pattern-scout**: before you implement any non-trivial toolkit module, puzzle mechanic, check, template, configurator field, or skill block, and any time you ask "how do we do X here?". Returns real code examples with the rules distilled from them.
- **adr-checker** (consult mode): before you implement in an ADR-relevant area (the "Architecture Decision Records (ADRs)" section lists them). Returns the decisions the work must follow.

**After you implement, before you ship:**

- **docs-checker**: after a change that could affect documented content. Checks every documentation location (code comments, the area `AGENTS.md` files, `README.md`, ADRs, contract descriptions, skill instructions, catalog files) against the code and fixes drift.
- **validate**: just before you create a PR or push. Runs the repo's checks the way CI does and reports pass or fail.
- **adr-checker** (maintain mode): after you introduce a new architectural pattern or change one that an ADR records. Creates or updates the ADR.

Beyond these, spawn subagents freely: hand off research, code exploration, and parallel analysis so the files they read stay out of your own context. Give each subagent one task.

## Writing style

The people who read your output may read English as a second language and may be new to the area. Two layers apply. This section is the one home for both: no other file restates them.

**Layer 1 covers every piece of prose you write**: chat replies, PR and issue text, review comments, commit messages, and every document below. It follows Zinsser's four principles, which are simplicity, brevity, clarity, and humanity.

- **Short sentences, one idea each.** Use common words. Avoid idioms, slang, and cultural references.
- **Lead with the answer**, then only the detail that changes what the reader does. Cut filler and hedging. Do not use em dashes.
- **Assume a short attention span.** The reader usually skims to make a quick decision (which PR to review, which issue to pick), with little context and little time; put the single most important thing first, and make each part land even if they stop after the first line.
- **Gloss each jargon term, acronym, or tool/library name on first use** in one short clause, or pick a simpler word.
- **Explain a concept briefly before going deeper.** Do not assume a flow, tool, or pattern is already known.
- **Assume junior-level knowledge of the area.** Name the things you reference (files, commands, terms) instead of assuming the reader can guess.

**Layer 2 adds ASD-STE100 on top, for technical documents only**: `AGENTS.md` and area docs, ADRs, `README.md`, skills, subagents, and code comments. ASD-STE100 (Simplified Technical English) is a controlled-English standard from the aerospace industry. A maintenance manual must carry one reading and one only, and these documents have the same job.

- **Active voice only.** Name the actor: "the hook formats the file", not "the file gets formatted".
- **One meaning per word, and the same word for the same thing every time.** Never swap in a synonym for variety.
- **One instruction per sentence, and start the sentence with the verb.** Write "Run the migration", not "The migration should be run".
- **No `-ing` verb form as a noun or as a sentence opener.** Write "Use the skill to create a branch", not "Creating a branch is done with the skill".
- **About 20 words per sentence at most** (25 in descriptive text).
- **Leave out no word that guards the meaning.** Write "the file that you changed" when "the file you changed" could be misread.

Both layers cover prose only. Neither covers code identifiers or text you quote word for word.

## Map

| Path            | What it is                                                                                                                                                             |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `configurator/` | The config page that a user opens with a double-click. Plain JavaScript, no build. Area doc: `configurator/AGENTS.md`.                                                 |
| `toolkit/`      | The Python toolkit (package `mystery_forge`, CLI `forge`): config, builders, checks, rendering. Area doc: `toolkit/AGENTS.md`.                                         |
| `generator/`    | The workspace that a user opens in the agent to generate a game: the generation guide, the pskill skills, and the game work folders (`generator/games/`, git-ignored). |
| `contracts/`    | Data that both the JavaScript and the Python side read. Each file has shared test vectors that both sides must pass.                                                   |
| `scripts/`      | Node development scripts. `generate-config-schema.js` copies the config schema into the configurator (`npm run generate:schema`).                                      |
| `examples/`     | Example config files.                                                                                                                                                  |
| `adr/`          | Architecture Decision Records.                                                                                                                                         |

## Commands

Run every command from the repo root unless the Notes column names another folder.

| Task                                           | Command                                                   | Notes                                                                                           |
| ---------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Install the JavaScript tools and the git hooks | `npm install`                                             | The `prepare` script runs `lefthook install`. Run it once per clone.                            |
| Install the Python toolkit                     | `cd toolkit && uv sync`                                   | uv installs Python 3.12 when it is missing.                                                     |
| Run every check, the way CI runs it            | `npm run check`                                           | `check:web`, then `check:toolkit`, then `check:skills`.                                         |
| Check the JavaScript side                      | `npm run check:web`                                       | Prettier check, `tsc` over the JSDoc types, `node --test` with 100% coverage thresholds.        |
| Check the toolkit                              | `npm run check:toolkit`                                   | `ruff format --check`, `ruff check`, `mypy` (strict), `pytest --cov` (100% lines and branches). |
| Check the generator skills                     | `npm run check:skills`                                    | `pskill validate` and `pskill test` in `generator/`.                                            |
| Format everything                              | `npm run format` and `cd toolkit && uv run ruff format .` | Prettier formats JavaScript, CSS, HTML, JSON, YAML, and Markdown.                               |
| Run the toolkit CLI                            | `cd toolkit && uv run forge --help`                       | The generator calls it as `uv run --project ../toolkit forge ...`.                              |

Whenever you need to confirm the code still passes, delegate to the **validate** agent (it runs the sequence above the way CI does).

## Rules

- **The agent writes content; code builds and checks mechanics.** A puzzle that code can build from its answer gets a builder, never hand-written puzzle material. `adr/0004-verification-strategy.md` has the order of preference.
- **One definition per shared rule.** A rule that both JavaScript and Python apply (answer normalization, config validation, the time estimate) lives once in `contracts/`, with test vectors that both sides run. Change the contract file and both implementations in the same PR.
- **Every toolkit CLI verb prints one small JSON object.** It exits 0 when it ran, also when it found problems, and 2 on a usage or environment error. Full reports go to files. pskill pauses a run on a non-zero exit and cuts stdout at 64 KiB.
- **Open every file with `encoding="utf-8"`.** The Windows console default (cp1252) breaks Spanish text. Ruff rule `PLW1514` enforces it.

## Gotchas

- **Claude Code loads every `CLAUDE.md` from the working folder up to the repo root.** An agent that generates a game in `generator/` therefore also sees this file. The first line of this file sends it away; keep that line.
- **pskill finds `.pskill/` only upward from the working folder.** Run every pskill command from `generator/`, never from the repo root.

## Test-Driven Development (mandatory)

Develop new behavior **test-first, red-green**: write a failing test that pins the behavior you want (**red**), make it pass with the smallest change (**green**), then clean up with the test as your safety net. A bug fix starts with a test that reproduces the bug.

- **Testable, always test-first:** every toolkit module (config, brief, builders, verifiers, checks, judge, loaders, render helpers), every configurator logic file, and every pskill skill path (one `tests/<case>.yaml` per path through the graph).
- **Thin glue, covered another way:** `configurator/app.js` (DOM wiring) and the browser launch in the toolkit. Playwright end-to-end tests open the real page and render real PDFs. Keep the glue thin: it reads or writes the DOM and holds no decision.
- **Coverage gates:** the toolkit fails below 100% of lines and branches, and the JavaScript logic files fail below 100% of lines, branches, and functions. Mark a line that no input can reach with `# pragma: no cover` and its reason; never use it to skip a hard case.

The gate: CI runs the tests on every PR, and the repo ruleset "Requirements for merge" blocks merging until the `checks (ubuntu-latest)` and `checks (windows-latest)` checks are green.

## Git Workflow

- Branch from `main`, PR back to `main`. Whenever you create a branch, use the `create-branch` skill.
- Conventional commits: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`. Whenever you commit, use the `write-commit` skill.
- PRs merge automatically once the required checks pass (`.github/workflows/auto-merge.yml`). There is no human review gate: the tests are the review, which is what makes the TDD protocol non-negotiable.

## Documentation Organization

Each kind of knowledge has one home. Write a change in the home that matches it; never duplicate the same content across homes. What decides the home is **when the file loads** and **how deep it goes**, not its subject.

| Home                             | Loaded                               | Holds                                                                                                                                                                        |
| -------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGENTS.md`                      | Every session                        | The map: architecture facts, conventions, gotchas, and the ADR index. Points to the homes below; does not repeat their depth. (`CLAUDE.md` is a one-line `@AGENTS.md` shim.) |
| `toolkit/AGENTS.md`              | On demand, when working in that area | The toolkit's module map, conventions, and gotchas. (Its `CLAUDE.md` is a one-line shim.)                                                                                    |
| `configurator/AGENTS.md`         | On demand, when working in that area | The configurator's file map, conventions, and gotchas. (Its `CLAUDE.md` is a one-line shim.)                                                                                 |
| `generator/AGENTS.md`            | Every session opened in `generator/` | The guide for an agent that generates a game. Not a development doc. (Its `CLAUDE.md` is a one-line shim.)                                                                   |
| `.claude/skills/<name>/SKILL.md` | On demand, when the task matches     | One procedure: how to do X.                                                                                                                                                  |
| `adr/NNNN-*.md`                  | On demand, via adr-checker           | One architectural decision and its why.                                                                                                                                      |
| `README.md`                      | Read by humans                       | What the project is, setup, use, printing, troubleshooting.                                                                                                                  |

**All of these files are living: keep them true.** When you learn something that helps future agents, update the right file in the same session. When a file holds wrong or outdated information, fix it or remove it. This covers code comments too. After implementation, the **docs-checker** agent catches drift you missed.

**Rules:**

- ADRs are agent-only: never reference or list them in a `README.md`.
- Number ADRs in sequence (`NNNN-kebab-title.md`) and never renumber an existing file. Index each one as a one-line row in the ADR table below, never a summary.
- Do not duplicate content between `README.md` and `AGENTS.md`; reference it instead.
- `CLAUDE.md` is a one-line `@AGENTS.md` shim; edit `AGENTS.md` instead.

## Architecture Decision Records (ADRs)

ADRs live in `adr/`. Each records one architectural decision or cross-cutting standard and why. **One ADR per pattern, kept alive:** when a pattern changes, update its ADR in place; create a new ADR only for a genuinely new pattern. Most changes need no ADR. Conventions: `adr/AGENTS.md` (auto-loads through its `adr/CLAUDE.md` shim when you work in `adr/`).

**Before implementing** in an area that may carry a decision, delegate to the **adr-checker** agent in consult mode. These areas usually carry decisions: the game source format and its loader, the config contract, the verification strategy (builders, checks, solver panel), the rendering stack, the generator flow, answer normalization, and the testing strategy.

**After implementing**, delegate to the **adr-checker** agent in maintain mode only if you introduced a new architectural pattern or changed one an ADR already records.

| ADR                                              | Topic                                                                                            |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `0001-agent-docs-structure.md`                   | `AGENTS.md` map + Claude-Code-only skills/subagents/settings, plus the separate generator guide  |
| `0002-python-toolkit-and-static-configurator.md` | Python toolkit run by uv, plain-JavaScript configurator page, and the cross-language contracts   |
| `0003-game-source-format.md`                     | A game is YAML and Markdown files that `forge assemble` turns into one validated model           |
| `0004-verification-strategy.md`                  | Builders first, then code verifiers, then the AI solver panel with its thresholds                |
| `0005-rendering-stack.md`                        | Jinja templates, fixed-size sheets, inlined fonts, Playwright with the system Chrome or Edge     |
| `0006-generator-flow.md`                         | The `create-game` pskill flow: orchestrator agent, subagent writers, scripts, fix loops          |
| `0007-testing-strategy.md`                       | Unit tests at 100%, contract vectors, end-to-end browser tests, recorded pskill cases, live runs |

## GitHub issues, PRs, and other artifacts

- **Always self-assign PRs** when you create them.
- **Always link PRs to issues** with `Closes #N` in the PR body, so the issue auto-closes on merge.
- **Always add the `waiting-for-human-check` label** when you create a GitHub issue, PR, or any other reviewable artifact. It means no human has verified the content yet; a human removes it after reviewing. The label marks state (unreviewed), not origin. Here it does not block the auto-merge.

If the repo has no `waiting-for-human-check` label, create it first:

```bash
gh label create "waiting-for-human-check" --description "No human has verified this yet -- direct AI output" --color "D93F0B"
```

Whenever you create a GitHub issue, use the `create-issue` skill. Whenever you implement one, use the `implement-issue` skill. When you want a review of a PR, use the `review-pr` skill (optional here, because the checks are the gate).

## Coding standards

- **Match existing patterns.** Before writing code, find similar implementations and follow their style, structure, and conventions (the **pattern-scout** agent does this).
- **Explicit type annotations** are mandatory for all parameters, return types, and non-trivial variables. Python: mypy strict. JavaScript: JSDoc types checked by `tsc`.
- **Comment the _why_, never the _what_.** A comment must carry what the code cannot: a non-obvious constraint, an intentional divergence, a trap a future reader would reintroduce. Do not document self-explanatory names or signatures, and match the comment density of the surrounding file.

## Refactoring safety

Whenever you rename or refactor a symbol, use the `rename-symbol` skill.

## Debugging

Whenever a fix attempt fails or a bug needs root-causing, use the `debug` skill.

## Writing prompts for agents and rules

Whenever you author or edit an AI-facing file (`AGENTS.md`, skills under `.claude/skills/`, subagents under `.claude/agents/`, the generator guide, pskill skills and agents under `generator/.pskill/`, prompts for agents you spawn), use the `write-ai-instructions` skill.

## Self-updating rules

These instruction files are living, and keeping them current is part of the work. Persist a rule right away (in the narrowest scope that fits) instead of applying it only this session when you discover something **extremely hard to find, deeply non-obvious, and time-saving for future sessions**, hit a pattern that **diverges from what an AI would write by default**, when the user says **"every time" / "always" / "never"**, or when **feedback on your own work reveals a standard you should have followed** (a PR review comment, a user correction). Persist it in these shared, committed files, never in personal memory or the global config, so the whole team gets the lesson. For where to write it, use the `write-ai-instructions` skill.
