{% set choice = steps.pick_concept.choice if steps.pick_concept is defined else steps.pick_concept_agent.choice %}{% set number = {'first': 1, 'second': 2, 'third': 3}[choice] %}Write the story bible of the game in `{{ steps.setup.json.game_dir }}`, from concept number {{ number }} of `source/concepts.yaml`.

Read first: `source/config.json`, `source/brief.json` (puzzle count, stages, reading budget), `source/draw.json` (the audience rule and the clichés to avoid), `source/concepts.yaml`, `uv run --project ../toolkit forge catalog rules`, and `uv run --project ../toolkit forge schema story`.

Write `{{ steps.setup.json.game_dir }}/source/story.yaml`, in the game language. It must hold:
- **The fact registry.** Every character, place, object, and true event, with an id. Give the timeline real times (`YYYY-MM-DD HH:MM`), places, and participants: the checks reject a person who is in two places at once. Set `known_to_players: true` on the events that the intro or the first documents tell.
- **The truth.** What really happened, step by step, in plain prose. It is the source for every document; nothing in the game may contradict it.
- **The deduction** (when the config format is `case_file` or `both`): the culprit (`is_culprit: true`, and `is_suspect: true` on every suspect), 2 to 4 multiple-choice questions (who, how or with what, why, and when it fits a question about a key piece of evidence), each with `proven_by` clues, and one `exclusions` entry per innocent suspect with the clues that clear them. Give the "who" question one option per suspect.
- **The story clues.** For each piece of evidence that the deduction cites, a clue with an id, the document id where it will appear (`D1`, `D2`, ... in the order that players will meet them; the planner keeps these ids), and the exact sentence that the document will contain (`quote`). Write each quote as a natural sentence from that kind of document.
- **The intro** (read aloud at the start: 80 to 160 words; it sets the scene, the goal, and the stakes), the **epilogues** (at least three: full success at 75%, partial success at 40%, failure at 0%), and the **reveal**: 3 to 6 steps of "how you could have known", each citing clues.
- `visual_style` only when the config's `visuals.style` is `auto`: the style that fits the story best.

Quality bar:
- A fair, surprising, and coherent mystery: every fact the solution needs is in the material, the twist is foreshadowed, and red herrings resolve.
- Specific details beat vague mood. Use real-feeling names, places, times, and objects.
- Respect the audience rule and the content limits in the config. No cliché names, phrases, or plots from `draw.json`.
- Weave the personalization of the config into the story when it is set (the place, the host, the inside jokes).

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope story` and fix every error before you answer.
Your answer is a spoiler-free summary.
