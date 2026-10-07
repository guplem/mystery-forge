Revise `{{ steps.setup.json.game_dir }}/source/story.yaml` for these review findings:

{% for finding in steps.review_story.results[0].findings %}- [{{ finding.severity }}] {{ finding.problem }} Fix: {{ finding.fix }}
{% endfor %}
- Fix every required finding with the smallest change that solves it.
- Apply a suggestion only when it costs little and adds no new clue, document, character, or event: every addition must be written, checked, and read later, and a larger story is slower to play.
- Keep the parts that the findings do not touch.

Edit the file with the Edit or Write tool (a long shell command fails on Windows). Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope story` and fix every error before you answer. Your answer is a spoiler-free summary.
