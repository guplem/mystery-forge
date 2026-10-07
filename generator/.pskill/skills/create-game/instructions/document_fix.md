Fix the required problems that the document review found in the game in `{{ steps.setup.json.game_dir }}`:

{% for finding in steps.review_documents.results[0].findings %}{% if finding.severity == 'required' %}- {{ finding.document }}: {{ finding.problem }} Fix: {{ finding.fix }}
{% endif %}{% endfor %}
Change only `source/documents/`, `source/story.yaml` (when the contradiction is in the story), and the puzzle files whose clue quotes must follow a changed sentence. Keep every clue quote and its document sentence identical, or change both together. Edit with the Edit tool.

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope full --no-write` and fix every error that your change caused.
