The game language `{{ steps.texts.json.language }}` has no checked table of the toolkit's fixed texts (the labels, the manual, the answer register, the companion page, the file names, and the dates). Translate them once for this game.

Read the English template `{{ steps.texts.json.template }}`. Write `{{ steps.texts.json.target }}` with the Write tool: the same JSON, with every value in the game language.
- `strings`: translate each value, and keep every key. Copy each `{field}` exactly, braces included: the code fills it in. Keep the style: short labels for buttons and headings, plain instructions for the manual, a friendly tone for players.
- Keys that start with `file_` name the exported files: keep them short, keep their number at the start, and use none of these characters: `< > : " / \ | ? *`.
- Keys that start with `list_` join a list, such as "a, b, and c": write the separator and the word "and" of the game language (for example `、` and `と` in Japanese).
- `months`: the 12 month names, January first. `weekdays`: the 7 day names, Monday first.
- `date_pattern`: the long date of the language, with `{day}`, `{month}`, and `{year}`.

Then run `uv run --project ../toolkit forge strings --game {{ steps.setup.json.game_dir }}` and fix every finding that it reports.
{% if history.translate_texts | length > 0 %}
The last check still found problems: {% for finding in steps.texts.json.findings | default([]) %}{{ finding.message }} {% endfor %}
{% endif %}