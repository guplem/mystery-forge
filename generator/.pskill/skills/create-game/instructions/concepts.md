Write three story concepts for the game in `{{ steps.setup.json.game_dir }}`.

Read first:
1. `{{ steps.setup.json.game_dir }}/source/config.json`: the audience, format, players, duration, language, theme idea, tone, content limits, and personalization.
2. `{{ steps.setup.json.game_dir }}/source/draw.json`: the drawn cards. Each concept must use one of the drawn settings, one goal, one twist, one frame, and one motif, and a different combination from the other concepts. When the config has a theme idea, every concept honors it and uses the cards to make it surprising.
3. `uv run --project ../toolkit forge catalog rules`: the design rules.

Write `{{ steps.setup.json.game_dir }}/source/concepts.yaml` with a list `concepts:` of exactly three entries. Each entry has:
- `title`: a title that makes people curious, in the game language. No cliché names or phrases from `draw.json`.
- `teaser`: two or three sentences for the back of a box: who you are, what happened, what is at stake. NO culprit, no twist, no solution.
- `setting`, `goal`, `twist`, `frame`, `motif`: the ids of the cards that it uses.
- `pitch`: one paragraph for the writers: the hidden truth, the culprit or the hidden mechanism, the twist, and the final "aha".
- `cast`: 3 to 6 characters, each in one line (name, role, why they matter). Use fresh, specific, culturally fitting names.
- `why_fun`: one line on why a group will enjoy it.

Make the three concepts really different from each other: in tone, in structure, and in what the players do.
Return only the teasers (titles and teasers, in order), a summary, and the concept that you recommend with one spoiler-free reason. Never put the pitch or a twist in your answer. Write the file with the Write tool (a long shell command fails on Windows).
