Write puzzle **{{ item.id }}** ({{ item.mechanic }}, stage {{ item.stage }}) of the game in `{{ steps.setup.json.game_dir }}`, and the documents that it owns: {% for document in item.documents %}`{{ document }}`{% if not loop.last %}, {% endif %}{% endfor %}.

Read first: `source/config.json`, `source/draw.json` (the audience rule), `source/story.yaml`, `source/flow.yaml`, the entry of {{ item.id }} in `source/plan.yaml`, {% if item.relies_on %}the story documents that it relies on ({% for document in item.relies_on %}`source/documents/{{ document }}.md`{% if not loop.last %}, {% endif %}{% endfor %}), {% endif %}`uv run --project ../toolkit forge catalog show {{ item.mechanic }}` (how the mechanic works, its params, its pitfalls, its hint ladder), `uv run --project ../toolkit forge schema puzzle`, and `uv run --project ../toolkit forge schema references`.

Write `source/puzzles/{{ item.id }}.yaml` and the documents `source/documents/<id>.md` that you own. Write no other file: other subagents write the other puzzles at the same time.
- **Answer and params.** Keep the planned answer unless it cannot work with the mechanic; then pick a better one and say so in your summary. For a built mechanic, give only the params: the toolkit builds the material, and you place it with `{{ '{{artifact}}' }}` in the document whose front matter has `puzzle: {{ item.id }}`.
- **The material.** The documents must make the puzzle solvable and fair: the key, the rule, or the needed facts appear somewhere the players have at this stage, with a clear but not obvious signpost. Hide nothing that the players cannot find.
- **Clues.** Each `clues` entry quotes, character for character, a sentence of a document that players have at this stage or earlier.
- **Solution.** Steps that a player could follow, each citing the clues it uses.
- **Hints.** Three hints: 1 = which materials you need, 2 = a nudge toward the method, 3 = the method. No hint contains the answer.
- **Answer variants.** `accepted` for spellings that also count, `near_misses` for likely wrong answers with a nudge message, and `decoys`: 3 plausible wrong answers from the story world for the paper answer register.
- **Canary.** Set `canary` to `canary-{{ item.id | lower }}-` followed by six random letters.
- **Meta and earlier answers.** When the puzzle depends on other puzzles, its material must say how to use their answers.

Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix every error in YOUR files (other puzzles may not exist yet). Your answer names your files and gives one line with no answer.
