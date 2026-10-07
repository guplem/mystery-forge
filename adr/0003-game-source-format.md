# Game source format: YAML and Markdown files assembled into one model

## Context

An LLM writes the game. Long prose inside one big JSON file is hard for an LLM to write without escape errors, and parallel subagents that edit one file lose each other's writes. YAML 1.1 loaders also change values silently: `answer: no` becomes `False`, and `answer: 0420` becomes a number.

## Decision

- A game work folder is `generator/games/<date>-<slug>/`. Its `source/` folder holds the files that agents write, and the toolkit writes the rest.
  - `config.json` and `brief.json`: the normalized user config and the derived numbers. The toolkit writes both.
  - `story.yaml`: the fact registry (characters, locations, objects, timeline events), the truth, the deduction, the intro, and the epilogues.
  - `plan.yaml`: the puzzle plan. It names the documents that each writer owns and the sentences (`must_contain`) that those documents must keep. `forge check` compares the written game with it.
  - `flow.yaml`: the stages (envelopes) in order and what opens each one.
  - `puzzles/<id>.yaml`: one puzzle each, with its answer, its mechanic parameters, its clues, its solution steps, and its hints.
  - `documents/<id>.md`: one player document each. Front matter holds the metadata; the body is Markdown with a small fixed set of directives.
  - `images/`: SVG files.
- Each parallel writer owns only its own files. Shared indexes are computed by the toolkit, never written by agents.
- **Every YAML scalar loads as text**, except `null`. Pydantic then converts each field to its declared type. `0420` stays `"0420"`.
- `forge assemble` loads everything, runs the puzzle builders, resolves the references in the documents, and writes `game.json`. The renderer reads only `game.json`.
- Every error names the file, the line when known, the field path, a rule id, and a fix hint, because fix loops read these errors.
- Every file carries `format_version: 1`. A change that breaks old games raises the version and adds a migration.

**Rejected alternative:** one `game.json` written by the agent. It is simpler to load, but it breaks under parallel writers and long prose.

## Consequences

- An agent can change one puzzle without touching the others, and a fix loop re-checks only what changed.
- The loader is the largest error surface, so its errors must stay precise and tested.
