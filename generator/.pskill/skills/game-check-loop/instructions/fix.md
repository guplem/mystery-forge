Fix the findings of the group **{{ item.name }}** in the game folder `{{ inputs.game_dir }}`.

- **The findings:** read `{{ item.findings_file }}`. Each finding names a rule, a file, often a line and a field path, a message, and a fix hint.
- **The files that you may change:** {% for file in item.files %}`{{ inputs.game_dir }}/source/{{ file }}`{% if not loop.last %}, {% endif %}{% endfor %}. Change no other file: other subagents fix the other groups at the same time.
- **Fix every error.** Fix a warning too when the fix is small and safe. When a finding is wrong (the check misread the game), leave it, and say so in your summary.
- **Keep what works.** Change the smallest part that fixes the finding. Do not rewrite a puzzle, a story, or a document that the findings do not touch.
- After your changes, run `uv run --project ../toolkit forge check --game {{ inputs.game_dir }} --scope {{ inputs.scope }}` and read the findings for your files only. Repeat until your files have no error, or until you cannot make progress.
