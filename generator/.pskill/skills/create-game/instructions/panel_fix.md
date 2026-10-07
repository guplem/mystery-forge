The solver panel failed **{{ item.code }}** with the verdict `{{ item.verdict }}`. Fix it in the game folder `{{ steps.setup.json.game_dir }}`.

- **The panel report for this item:** `{{ item.findings_file }}`. It has the solvers' answers, their evidence, the other answers that they considered, and where they got stuck.
- **The files that you may change:** {% for file in item.files %}`{{ steps.setup.json.game_dir }}/source/{{ file }}`{% if not loop.last %}, {% endif %}{% endfor %}.

What each verdict asks:
- `ambiguous`: a second answer fits. Add or sharpen a clue that rules it out, or add it to `accepted` when it truly means the same thing.
- `gold_suspect`: several solvers agree on another answer with good evidence. First check whether the official answer is wrong; fix the answer or the material.
- `too_hard`: the solvers could not reach the answer. Make the signpost or the key clearer, or move a needed fact to a document that players have at this stage. Do not make it trivial.
- `guessable`: the answer can be guessed from the premise. Change the answer to something specific that only the material gives, and update every place that uses it (puzzles that depend on it, the stage that it opens).
- `trivial`: the material states every step of the method, so solving it takes no insight. First remove each sentence that explains the method, the order of operations, or what the result means; keep only the signpost that says where to look. When the built material itself is the method (the puzzle only follows stated rules), answer `failed` and say so in your summary: the puzzle needs another mechanic.
- `puzzles_not_needed` (the deduction item): solvers who solved no puzzle still proved this accusation answer from the plain documents. The `puzzles_not_needed` list of the report quotes the sentences that they used. Remove or blur those facts in the plain documents, so that the proof needs the hidden clue that a puzzle reveals. A fact can leak in other words, or from two documents together: blur every route that the solvers quoted. Keep every plain clue that `story.yaml` cites word for word; when a plain clue itself gives the answer away, change the clue in `story.yaml` and in its document together. When every innocent suspect is cleared by plain documents, make one clearance depend on a hidden clue.
- `insufficient_solvers`: too few solvers ran. Change nothing, and answer `kept`.

When you are sure that the solvers missed a clue that is clearly there, answer `kept`, and quote the sentence in your summary. Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix the errors in your files.
