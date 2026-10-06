Fix the required layout problems that the visual review found in the game in `{{ steps.setup.json.game_dir }}`:

{% for finding in steps.visual_review.results[0].findings %}{% if finding.severity == 'required' %}- {{ finding.page }}: {{ finding.problem }} Fix: {{ finding.fix }}
{% endif %}{% endfor %}
Change only the source files of the game (`source/documents/`, `source/images/`, and the `params` of a puzzle when its material is too big). Change no fact, no clue quote, and no answer: a changed text must keep every quoted clue sentence word for word. Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix any new error.
