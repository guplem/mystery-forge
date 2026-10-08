{% set forced = steps.export_with_warnings is defined %}{% set exported = steps.export_with_warnings.json if forced else steps.export.json %}{% set warnings = exported.warnings | default([]) %}Tell the user that their game is ready, in the folder `{{ exported.folder }}`. List the files that it holds, one line each, with what each is for:
{% for file in exported.files %}- {{ file }}
{% endfor %}
Then say, in short lines:
- What to do now: open the file whose name starts with "1 -" first (the manual); it has the printing checklist.
- How it was tested: {{ history.panel | length }} solver panel round(s){% if not inputs.panel %}; the solver panel was turned off for this run{% endif %}.
{% if warnings %}- Some tests did not pass, so the game was exported with warnings. The file whose name starts with "0 -" in the game folder lists them for the host. Name each one in plain words, in the user's language, without the puzzle content:
{% for warning in warnings %}  - {{ warning }}
{% endfor %}- The game is probably playable. To fix the warnings, they can ask you here, for example "fix the warnings of this game".
{% endif %}- The game's source stays in `{{ steps.setup.json.game_dir }}`. To change something later, they can ask you here (for example: "make puzzle B2 easier", "print it in black and white").

Do not reveal any answer, culprit, twist, or puzzle content: the user may play this game.
