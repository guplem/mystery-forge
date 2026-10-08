The solver panel failed **{{ item.code }}** with the verdict `{{ item.verdict }}`. Fix it in the game folder `{{ steps.setup.json.game_dir }}`.

- **The panel report for this item:** `{{ item.findings_file }}`. It has the solvers' answers, their evidence, the other answers that they considered, and where they got stuck.
- **The files that you may change:** {% for file in item.files %}`{{ steps.setup.json.game_dir }}/source/{{ file }}`{% if not loop.last %}, {% endif %}{% endfor %}.

{% set earlier = [] %}{% for round in history.panel[:-1] %}{% for line in round.outputs.failing %}{% if line.startswith(item.code ~ ':') %}{% set _ = earlier.append(line) %}{% endif %}{% endfor %}{% endfor %}{% if earlier %}This item also failed earlier panel rounds: {{ earlier | join('; ') | truncate(400) }}. A text edit did not help, so change the mechanic, the params, or the answer this time.

{% endif %}Limits for every fix:
- Never add the method, the order of steps, or the meaning of the result in the voice of the character who hides the answer: a hider does not explain the code. Keep each limit in the `notes` of this puzzle in `plan.yaml`.
- The same verdict after an earlier fix means that more text will not help: change the mechanic, the params, or the answer instead.

What each verdict asks:
- `ambiguous`: a second answer fits. Add or sharpen a clue that rules it out, or add it to `accepted` when it truly means the same thing.
- `gold_suspect`: several solvers agree on another answer with good evidence. First check whether the official answer is wrong; fix the answer or the material.
- `too_hard`: the solvers could not reach the answer. Make the signpost or the key clearer, or move a needed fact to a document that players have at this stage. Do not make it trivial.
- `guessable`: the answer can be guessed from the premise. Change the answer to something specific that only the material gives, and update every place that uses it (puzzles that depend on it, the stage that it opens).
- `incomplete`: most solvers got the answer, but they had to assume a step that the material does not support. The report lists each gap. Add the missing link or fact to the document that should carry it (often a sentence that a fix removed earlier); keep it a signpost, not the method.
- `trivial`: the material states every step of the method, so solving it takes no insight. First remove each sentence that explains the method, the order of operations, or what the result means. Keep only the signpost that says where to look, and an in-world pointer to the extraction step (which letters, which order) when players could not guess it. When the built material itself is the method (the puzzle only follows stated rules), change the mechanic or its params instead: for example, move a printed key to other props (`key_parts`), or pick another implemented mechanic (`uv run --project ../toolkit forge catalog list`) that hides the same answer, and rewrite the puzzle and its documents for it. Keep the answer.
- `puzzles_not_needed` (the deduction item): solvers who solved no puzzle still proved this accusation answer from the plain documents. The `puzzles_not_needed` list of the report quotes the sentences that they used. Remove or blur those facts in the plain documents, so that the proof needs the hidden clue that a puzzle reveals. A fact can leak in other words, or from two documents together: blur every route that the solvers quoted. Keep every plain clue that `story.yaml` cites word for word; when a plain clue itself gives the answer away, change the clue in `story.yaml`, in its document, and in the `must_contain` of `plan.yaml` together. When every innocent suspect is cleared by plain documents, make one clearance depend on a hidden clue.
- `insufficient_solvers`: too few solvers ran. Change nothing, and answer `kept`.

When you change the params or the mechanic, run `uv run --project ../toolkit forge material --game {{ steps.setup.json.game_dir }} --puzzle <puzzle id>` and check that the hints and the solution still describe the material that it prints.

When you are sure that the solvers missed a clue that is clearly there, answer `kept`, and quote the sentence in your summary. Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix the errors in your files.
