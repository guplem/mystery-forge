# Mystery Forge generator

You are in the workspace that generates printable mystery games. **To make a game, run the pskill skill `create-game`.** It gives you one step at a time and checks each answer. Do not generate a game by hand, and do not skip or reorder its steps.

Start it with the user's config file, or with none (the skill then looks for the newest `*.mystery-config.json` in the Downloads folder):

```bash
uv run .pskill/pskill.py start create-game --input config="<path to the .mystery-config.json, or empty>"
```

Add `--mode autonomous` when the user asks you to decide everything alone (for example: "do not ask me anything"). In autonomous mode the run asks no questions.

**To change or fix a finished game** ("make puzzle B2 easier", "print it in black and white", "fix the warnings"), run `uv run --project ../toolkit forge games` to find its folder by title, then start the same skill with `--input game=<game_dir> --input change="<the request>"`. The run applies the change, checks, tests, renders, and exports a new copy. Never change a finished game outside such a run.

When a run already exists (the user says "continue"), run `uv run .pskill/pskill.py runs --open` and continue the open run with `uv run .pskill/pskill.py current <run>`. Never start a second run for the same game.

## What you must never do

- **Never read a file of a game that a step did not tell you to read**, and never paste answers, hints, or solutions into the chat. The person who runs the generator often plays the game too.
- **Never edit `source/config.json`, `source/brief.json`, `source/draw.json`, `game.json`, or anything in `reports/`.** The toolkit writes them.
- **Never invent a mechanic.** Use only the mechanics that `forge catalog list --implemented` shows.
- **Never write puzzle material that a builder can build.** For a built mechanic, write the answer and the params; the toolkit builds the cipher, the grid, or the maze.
- **Never change the toolkit or the skills** (`../toolkit/`, `.pskill/`) to make a game pass a check. Fix the game files instead. A real toolkit bug goes to the user as a short note at the end.
- **Never read the toolkit's source code** to learn what a check wants. The finding messages, `forge catalog rules`, and `forge schema` say everything that you need.
- **Never pause an autonomous run because a subagent stopped.** In an autonomous run nobody can interrupt you. A subagent that fails, stalls, or returns "Request interrupted by user" lost its connection: run the same task again. Pause only when the user really asks for it.
- **Never run a shell command longer than about 5,000 characters.** On Windows it fails or gets cut. Write files with the Write tool, and submit a long pskill answer from a file: `uv run .pskill/pskill.py submit <run> < answer.yaml`.

## The toolkit

Every command runs from this folder as `uv run --project ../toolkit forge <verb>`. Each verb prints one JSON object.

| Verb                                                       | What it does                                                                                  |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `forge catalog list --implemented`                         | The mechanics that you can use, with their player action and verification level.              |
| `forge catalog show <id>`                                  | One mechanic: how it works, its pitfalls, its hint ladder, and the JSON schema of its params. |
| `forge catalog rules`                                      | The design rules for game writers (pacing, fairness, hints, variety, failure modes).          |
| `forge schema <story\|flow\|puzzle\|document\|references>` | The fields of a source file, or the reference forms and directives of a document body.        |
| `forge assemble --game <dir>`                              | Load and build the game, and write `game.json`. Reports problems as findings.                 |

The skill's steps run the other verbs (doctor, setup, config, games, check, plain-test, writer-tasks, material, packets, judge, render, status, export) for you.

## A game folder

`games/<date>-<slug>/` (git-ignored). The agents write `source/`; the toolkit writes the rest.

| Path                                            | Written by                    | Holds                                                                                                                           |
| ----------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `source/config.json`, `brief.json`, `draw.json` | toolkit                       | The user's config, the derived numbers (puzzle count, stages), and the drawn story ingredients and mechanic candidates.         |
| `source/concepts.yaml`                          | concept writer                | Three story concepts.                                                                                                           |
| `source/story.yaml`                             | story writer                  | The fact registry (characters, places, objects, timeline), the truth, the clues of the deduction, the intro, and the epilogues. |
| `source/plan.yaml`, `source/flow.yaml`          | puzzle planner                | The puzzle plan and the stages (envelopes).                                                                                     |
| `source/puzzles/<id>.yaml`                      | puzzle writers                | One puzzle each: answer, params, clues, solution, hints.                                                                        |
| `source/documents/<id>.md`                      | puzzle and document writers   | One player document each: front matter plus a Markdown body.                                                                    |
| `source/images/<id>.svg`                        | document writers, illustrator | Simple SVG illustrations. The illustrator runs only when the config asks for SVG images.                                        |
| `game.json`, `reports/`, `render/`              | toolkit                       | The assembled game, the check reports, and the rendered files.                                                                  |

## Writing rules for every writer

- **Write in the game language** (`config.json` → `language`). Ids stay in English kebab case.
- **Use the fact registry.** Write `{{char:ana-ruiz}}`, `{{place:kitchen}}`, `{{event:theft.date}}` in document bodies and header `fields` instead of retyping names and dates. The toolkit fills them in, so every document agrees.
- **Quote, do not paraphrase.** A clue's `quote` is copied character for character from its document. The checks reject a quote that is not in the document.
- **Every puzzle needs a reason to exist in the story.** A coded line in a logbook is a puzzle; "Puzzle 4: decode this" is a worksheet.
- **Avoid the clichés** listed in `source/draw.json` (`cliches`): the overused names, phrases, and plots.
- **Respect the audience rule** in `source/draw.json` (`audience_rule`): words per document, murder or not, themes to avoid.
- **YAML:** quote a value that contains `: `, `#`, or a leading `{`, `[`, `*`, or `'`. Write numbers that must keep their zeros as text (`answer: "0420"`).
