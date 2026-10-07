# Mystery Forge

Make your own printable mystery game with an AI agent. You choose the players, the length, the difficulty, the language, and the look. The agent writes a story, builds the puzzles, tests them with a panel of AI players, and gives you PDFs to print plus a companion page for your phone or computer.

Every game is new: the story, the suspects, the puzzles, and the twist come from a random draw of story ingredients and a catalog of more than 90 puzzle types.

![The configurator: you choose who plays, the length, the story, and the look](docs/images/configurator.png)

| A printed page                                                       | The companion on a phone                                                                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| ![A newspaper page from a sample game](docs/images/printed-page.png) | ![The companion start screen, with the clock and the envelopes](docs/images/companion.png) |

A finished sample game to print: see the latest GitHub release.

## What you get

A folder on your Desktop (`Mystery Forge/<game title>`) with:

| File                                     | What it is                                                                                                                                           |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `1 - START HERE (manual).pdf`            | The printing checklist, how to set up the envelopes, and how to play. Read it first.                                                                 |
| `2 - PRINT THIS (game materials).pdf`    | The game: letters, reports, maps, codes, and puzzles, split into envelopes by "STOP" cover sheets, plus the answer register and the accusation form. |
| `Game companion.html`                    | One page for a phone or a computer: it checks answers, gives one hint at a time, keeps the time, and scores the accusation. It works offline.        |
| `HOST ONLY - spoilers/3 - Hints.pdf`     | Fold-over hint cards, for groups with no device.                                                                                                     |
| `HOST ONLY - spoilers/4 - Solutions.pdf` | Every answer and the full truth, behind a warning page.                                                                                              |

The file and folder names follow the game language. A Spanish game, for example, starts with `1 - EMPIEZA AQUÍ (manual).pdf`.

## What you need

- **A paid Claude plan (Pro or Max), or Anthropic API credits.** Claude Code runs on it. Mystery Forge itself is free.
- **Time and usage.** One game takes about 1 to 2 hours. It uses a large part of one usage window (the amount of use that your plan allows in a few hours). With API credits, you pay for that use.
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, a small tool that installs Python and the rest by itself.
- **[Claude Code](https://claude.com/claude-code)**, the AI agent that writes the game.
- **Google Chrome or Microsoft Edge**, to print the PDFs. (Without them, the agent can install a small browser for you.)
- This repository: click **Code → Download ZIP** on GitHub and unzip it, or clone it with git.

## Make a game

1. **Configure.** Open `configurator/index.html` with a double-click. It opens in your browser, with no internet needed. Pick who plays, how long, the story mood, what you can print, and so on. Click **Download config**: your browser saves a `.mystery-config.json` file in your Downloads folder.
2. **Generate.** Open Claude Code in the `generator` folder of this repository (see [Never used a terminal?](#never-used-a-terminal) below). The first time, Claude Code asks whether you trust the folder: say yes, so that its settings and hooks load. Say: **"create a game"**. The agent finds the newest config in your Downloads folder, shows you a summary, and asks you to pick one of three story teasers. After that it asks nothing more, so you can leave. A game takes about 1 to 2 hours, and it uses a large part of an AI usage window.
3. **Print and play.** Open the manual (the file whose name starts with `1 -`) and follow its printing checklist.

To change a finished game ("make puzzle B2 easier", "print it in black and white"), ask the agent in the same `generator` folder. If a generation stops halfway (for example at a usage limit), open Claude Code in `generator` again and say "continue".

## Never used a terminal?

A terminal is a window where you type commands. You need it to install the tools once and to start Claude Code. The install pages of [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Claude Code](https://claude.com/claude-code) each give one command: paste it into the terminal and press Enter.

**Windows**

1. Open File Explorer and go to the `generator` folder inside the Mystery Forge folder.
2. Click the address bar at the top, type `cmd`, and press Enter. A black window opens in that folder.
3. Type `claude` and press Enter.

**macOS**

1. Open Finder and find the `generator` folder inside the Mystery Forge folder.
2. Right-click the folder and choose **New Terminal at Folder**. (It can be under **Services**.)
3. Type `claude` and press Enter.

Then, on both systems:

1. Claude Code asks whether you trust the folder. Say yes.
2. Type **create a game** and press Enter.

## Printing tips

- Print at **100% (actual size)**, single-sided. "Fit to page" breaks grids and cut-out pieces. Where to find the setting:
  - **Chrome**: in the Print window, click **More settings**. Under **Scale**, choose **Actual size**.
  - **Edge**: in the Print window, click **More settings**. Under **Scale**, choose **Actual size**.
  - **Adobe Acrobat Reader**: in the Print window, under **Page Sizing & Handling**, click **Actual size**.
- A black-and-white printer is fine: choose it in the configurator, and the game uses patterns instead of colors.
- Split the printed stack at each **STOP** page without reading the pages, and put each part in its own envelope (or fold it and clip it).

## How the games stay correct

AI models make mistakes, so the agent never checks its own puzzles by eye:

- **Code builds the puzzles** that code can build (ciphers, grids, mazes, logic puzzles, locks), so they are correct by construction. The printed pages are read back and decoded again.
- **Code checks the whole game**: every clue is quoted from a real document, no answer leaks early, no character is in two places at once, each innocent suspect can be cleared, and the game fits the time you asked for.
- **A panel of AI players** gets only what real players have at each stage and tries to solve it. A puzzle that most of them cannot solve, or that has a second good answer, goes back for a fix. A second group reads only the plain documents and tries to accuse without solving any puzzle: if they can, the case goes back for a fix, because the puzzles must matter.

## Troubleshooting

| Problem                                         | What to do                                                                                           |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| The configurator page looks empty               | Keep the whole `configurator` folder together; the page needs its sibling files.                     |
| The agent says "no config found"                | Save the config from the configurator first, or give the agent the path of the file.                 |
| "No browser found"                              | Install Chrome or Edge, or let the agent install Playwright's Chromium.                              |
| The run stopped                                 | Open Claude Code in `generator` again and say "continue".                                            |
| The agent asks for permission for every command | Open Claude Code in the `generator` folder itself, not in the repository root, so its settings load. |

## For developers

The project is built and maintained with AI agents. The development map is in `AGENTS.md`.

```bash
npm install
npm run check
```

`npm run check` runs every check that CI runs: the JavaScript format, types, and tests, the Python toolkit format, lint, types, and tests (100% coverage), and the generator skill tests.

## License

MIT. See `LICENSE`. The bundled fonts keep their own open licenses, in `toolkit/src/mystery_forge/render/fonts/LICENSES/`.
