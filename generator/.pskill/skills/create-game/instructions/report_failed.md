Tell the user that the game is not finished: some checks still fail after every fix round, so nothing was exported. The game's files are in `{{ steps.setup.json.game_dir | default('the games folder') }}`, and the check reports are in its `reports/` folder.

Name the kind of problem that is left in one or two short lines, without any answer or spoiler. Offer two ways forward: run the generation again with a new story, or ask you to continue fixing this game.
