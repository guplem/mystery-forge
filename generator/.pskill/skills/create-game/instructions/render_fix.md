The render of the game in `{{ steps.setup.json.game_dir }}` found problems in the group **{{ item.name }}**. Read them in `{{ item.findings_file }}`.

You may change only these files: {% for file in item.files %}`{{ steps.setup.json.game_dir }}/source/{{ file }}`{% if not loop.last %}, {% endif %}{% endfor %}.

- `render.overflow`: the content does not fit on its sheet. Shorten the text, or split the document with a `::: pagebreak` directive (an empty block: `::: pagebreak` then `:::`) at a natural break.
- `render.roundtrip`: the printed puzzle does not decode to its answer. Check the params and the answer of the puzzle against `forge catalog show <mechanic>`.
- `render.leak`: an answer appears in clear text in printed material that players have before they solve it. Rewrite that text.
- Any other rule: follow its fix hint.

Change no fact of the story and no answer unless the finding needs it. Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix any new error in your files.
