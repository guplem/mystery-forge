{% set choice = steps.pick_concept.choice if steps.pick_concept is defined else steps.pick_concept_agent.choice %}{% set number = {'first': 1, 'second': 2, 'third': 3}[choice] %}Write the story bible of the game in `{{ steps.setup.json.game_dir }}`, from concept number {{ number }} of `source/concepts.yaml`.

Read first: `source/config.json`, `source/brief.json` (puzzle count, stages, reading budget), `source/draw.json` (the audience rule and the clichés to avoid), `source/concepts.yaml`, `uv run --project ../toolkit forge catalog rules`, and `uv run --project ../toolkit forge schema story`.

Write `{{ steps.setup.json.game_dir }}/source/story.yaml`, in the game language, with the Write tool (a long shell command fails on Windows). It must hold:
- **The fact registry.** Every character, place, object, and true event, with an id. Give the timeline real times (`YYYY-MM-DD HH:MM`), places, and participants: the checks reject a person who is in two places at once. Set `known_to_players: true` on the events that the intro or the first documents tell.
- **The truth.** What really happened, step by step, in plain prose. It is the source for every document; nothing in the game may contradict it.
- **The clues.** Two kinds:
  - **Plain clues:** a fact that a document prints. Give the clue an id, the document id where it will appear (`D1`, `D2`, ... in the order that players meet them; the planner keeps these ids), and the exact sentence that the document will contain (`quote`), written as a natural sentence from that kind of document.
  - **Hidden clues** (`hidden: true`, no `document`): 3 to 5 key facts that NO document prints in clear text, because a puzzle reveals them (a time, a place, an object, a number, a name on a list). In `quote`, state the fact in plain words. Leave `revealed_by` empty: the planner picks the puzzle. These are what make the puzzles matter.
- **The deduction** (when the config format is `case_file` or `both`): the culprit (`is_culprit: true`, and `is_suspect: true` on every suspect), 2 to 4 multiple-choice questions (who, how or with what, why, and a question about a key piece of evidence), and one `exclusions` entry per innocent suspect.
  - In `proven_by`, list only the 3 to 5 clues of the shortest proof. Every question needs a hidden clue: the puzzles must matter for the accusation.
  - Every wrong option is plausible: a document makes it tempting (a red herring with an innocent explanation). No joke options.
  - No single document names the culprit's act in their own words (no confession, no written plan, no motive spelled out by the culprit). The players must combine at least two clues.
  - Clear at least one innocent suspect by inference (two facts that together rule them out), not only by a timestamped alibi.
  - **The plain clues leave the case open.** With the plain clues alone, at least two suspects still fit, and each question that cites a hidden clue still has two defensible options. So clear at least one innocent suspect only with a hidden clue (cite it in that exclusion). Never state a hidden fact in other words in a plain clue or in the intro. The checks reject a culprit that plain clues name by elimination, and solvers who get no puzzle later test the rest.
- **The intro** (read aloud at the start: 80 to 160 words; who the players are, the goal, and the stakes), the **epilogues** (at least three: full success at 75%, partial success at 40%, failure at 0%), and the **reveal**: 3 to 6 steps of "how you could have known", each citing clues.
- `visual_style` only when the config's `visuals.style` is `auto`: the style that fits the story best.

Quality bar:
- A fair, surprising, and coherent mystery: every fact the solution needs is in the material or behind a puzzle, the twist is foreshadowed, and red herrings resolve.
- The obvious suspect is not the culprit, or the obvious suspect gets real cover early (an alibi that seems solid until a puzzle breaks it).
- Specific details beat vague mood. Use real-feeling names that fit the place and the era, places, times, and objects.
- Respect the audience rule and the content limits in the config. No cliché names, phrases, or plots from `draw.json`.
- Weave the personalization of the config into the story when it is set (the place, the host, the inside jokes).

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope story` and fix every error before you answer.
Your answer is a spoiler-free summary.
