Fix the required layout problems that the visual review found in the game in `{{ steps.setup.json.game_dir }}`:

{% for finding in steps.visual_review.results[0].findings %}{% if finding.severity == 'required' %}- {{ finding.page }}: {{ finding.problem }} Fix: {{ finding.fix }}
{% endif %}{% endfor %}
Change only the source files of the game (`source/documents/`, `source/images/`, the `params` of a puzzle when its material is too big, and the `hints` and `solution` of a puzzle). Change no fact, no clue quote, and no answer: a changed text must keep every quoted clue sentence word for word. The text of a hint or a solution step is yours: fix it in `hints` or `solution` of `source/puzzles/<id>.yaml`, so that it describes the printed material (`uv run --project ../toolkit forge material --game {{ steps.setup.json.game_dir }} --puzzle <id>` prints it as text). The layout of a page that the toolkit builds (the register, the results, the hint cards, the manual) is not yours: leave it and say so in your summary.

Then verify: `uv run --project ../toolkit forge render --game {{ steps.setup.json.game_dir }} --no-write` must report no error.
