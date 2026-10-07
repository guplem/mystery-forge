Read every player document of the game in `{{ steps.setup.json.game_dir }}` against the story bible, like an editor before print. Read `source/story.yaml`, `source/flow.yaml`, `source/plan.yaml`, every file in `source/documents/`, and the puzzle files in `source/puzzles/` (for their answers, so that you can spot a leak). Do not change any file.

Report:
1. **Contradictions** between a document and `story.yaml`, or between two documents: a time, a date, a place, a name, a number, who knew what, who did what. Quote both sides.
2. **Possession:** a document that the players hold with no story reason (a private letter of the culprit, a telegram addressed to someone else), unless the intro or another document explains how it reached them.
3. **Leaks:** a puzzle answer, a hidden clue, or an accusation answer stated in clear text in a document that players have before they earn it; a confession or a written plan of the culprit.
4. **Worksheets:** a puzzle document that explains the full method of its puzzle.
5. **Designer words:** text that talks about "the players", "this puzzle", internal ids such as P3 or D12, or instructions that break the fiction where the fiction would do.

A finding is `required` for a contradiction, a leak, a confession, or designer words. Everything else is a `suggestion`. Name the document id, quote the problem, and give a concrete fix that keeps every clue quote word for word. Return an empty list when the documents are ready.
