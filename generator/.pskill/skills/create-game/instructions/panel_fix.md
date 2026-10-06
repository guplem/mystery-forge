The solver panel failed **{{ item.code }}** with the verdict `{{ item.verdict }}`. Fix it in the game folder `{{ steps.setup.json.game_dir }}`.

- **The panel report for this item:** `{{ item.findings_file }}`. It has the solvers' answers, their evidence, the other answers that they considered, and where they got stuck.
- **The files that you may change:** {% for file in item.files %}`{{ steps.setup.json.game_dir }}/source/{{ file }}`{% if not loop.last %}, {% endif %}{% endfor %}.

What each verdict asks:
- `ambiguous`: a second answer fits. Add or sharpen a clue that rules it out, or add it to `accepted` when it truly means the same thing.
- `gold_suspect`: several solvers agree on another answer with good evidence. First check whether the official answer is wrong; fix the answer or the material.
- `too_hard`: the solvers could not reach the answer. Make the signpost or the key clearer, or move a needed fact to a document that players have at this stage. Do not make it trivial.
- `guessable`: the answer can be guessed from the premise. Change the answer to something specific that only the material gives, and update every place that uses it (puzzles that depend on it, the stage that it opens).
- `insufficient_solvers`: too few solvers ran. Change nothing, and answer `kept`.

When you are sure that the solvers missed a clue that is clearly there, answer `kept`, and quote the sentence in your summary. Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix the errors in your files.
