The render of the game in `{{ steps.setup.json.game_dir }}` found problems in the group **{{ item.name }}**. Read them in `{{ item.findings_file }}`.

You may change only these files: {% for file in item.files %}`{{ steps.setup.json.game_dir }}/source/{{ file }}`{% if not loop.last %}, {% endif %}{% endfor %}.

- `render.overflow`: the content does not fit on its sheet. The message says by how much and what. Shorten the text, or split the document with a page break (a line `::: pagebreak` followed by a line `:::`) at a natural break.
- `render.roundtrip`: the printed puzzle does not decode to its answer. Check the params and the answer of the puzzle against `forge catalog show <mechanic>`.
- `render.leak`: an answer appears in clear text in printed material that players have before they solve it. Rewrite that text.
- A problem that is not in your files (for example on a page that the toolkit builds): change nothing and answer `unfixable`, with the reason.

Change no fact of the story and no answer unless the finding needs it, and keep every clue quote word for word. Then verify your fix: `uv run --project ../toolkit forge render --game {{ steps.setup.json.game_dir }} --no-write --only {{ item.files | join(',') }}` must report no error for your files.
