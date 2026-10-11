Write the music suggestions of the game in `{{ steps.setup.json.game_dir }}`: `source/music.yaml`. The manual prints them, so hosts can play background music that fits the story.

Read first: `source/config.json` and, from `source/story.yaml`, only the spoiler-free fields `title`, `premise`, `setting`, `era`, and `tone`. Do not read the truth, the clues, the deduction, or any puzzle. Then run `uv run --project ../toolkit forge schema music`.

Write `source/music.yaml` with the Write tool: `format_version: 1` and 3 to 5 `suggestions`, each with a `title` and an `artist` (the artist, the composer, or the soundtrack).
- Suggest only real works that exist. Never invent a title or an artist.
- Match the story's setting, era, tone, and themes. A chess-themed fashion show fits the soundtrack of *The Queen's Gambit* better than a generic detective playlist.
- Prefer instrumental pieces and film or game soundtracks: players read a lot, and lyrics distract them.
- Keep each title in its original form. Write the rest of the file in the game language (a soundtrack name such as "Banda sonora de ..." follows the game language).
- Write no link, no URL, and no streaming service name: the printed manual stays self-contained.
- Never name or hint at a puzzle answer, the culprit, a twist, or a hidden clue. Also avoid a work whose title or artist shares a name with a character.

Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix every error in `music.yaml` (errors in puzzle files that do not exist yet are expected). Your answer lists the files that you wrote, with a spoiler-free summary.
