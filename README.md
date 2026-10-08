# Mystery Forge

Make your own printable mystery game for a party, a family dinner, or a quiet evening alone. You choose who plays, how long it lasts, and the language. An AI writes a new story with suspects, clues, and puzzles, tests it, and gives you files to print. You play at the table with paper, pencils, and envelopes.

![The configurator: you choose who plays, the length, the story, and the look](docs/images/configurator.png)

| A printed page                                                       | The companion on a phone                                                                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| ![A newspaper page from a sample game](docs/images/printed-page.png) | ![The companion start screen, with the clock and the envelopes](docs/images/companion.png) |

## How it works, in four steps

1. **Install two free programs, once** (about 10 minutes). See [Install, once](#install-once).
2. **Choose your game** on a web page: who plays, how long, what kind of story. The page saves a small file.
3. **Let the AI make the game** (about 1 to 2 hours, mostly waiting). You answer one or two questions at the start.
4. **Print and play.** Open the file whose name starts with `1 -`. It tells you what to print and how to set up the envelopes.

## What you need

- **A computer** with Windows or macOS.
- **A paid Claude account** (Claude Pro or Claude Max). The AI that writes the game runs on it. Mystery Forge itself is free. One game uses a large part of what your plan allows in a few hours, so plan to make one game at a time.
- **Google Chrome or Microsoft Edge** (Windows has Edge already). It turns the game into PDF files.
- **A printer.** Black and white is fine.

## Install, once

You do this only the first time. You will copy a few commands into a **terminal**: a window where you type instructions to the computer. Copy each command exactly, paste it, and press **Enter**.

### 1. Download Mystery Forge

1. On the GitHub page of this project, click the green **Code** button, then **Download ZIP**.
2. Find the downloaded file (usually in your **Downloads** folder) and unzip it: on Windows, right-click it and choose **Extract All**; on macOS, double-click it.
3. Move the unzipped `mystery-forge` folder somewhere easy to find, such as your **Documents** folder.

### 2. Open a terminal

- **Windows:** click the Start button, type **PowerShell**, and press Enter.
- **macOS:** press **Command + Space**, type **Terminal**, and press Enter.

### 3. Install uv (it installs everything else that Mystery Forge needs)

Paste the command for your computer and press Enter:

- **Windows (PowerShell):**

  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

- **macOS (Terminal):**

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 4. Install Claude Code (the AI that writes the game)

- **Windows (PowerShell):**

  ```powershell
  irm https://claude.ai/install.ps1 | iex
  ```

- **macOS (Terminal):**

  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  ```

Then **close the terminal window**, so that the computer finds the new programs next time.

If a command fails, the official pages always have the current one: [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Claude Code](https://claude.com/claude-code).

### 5. Sign in to Claude

Open a new terminal, type `claude`, and press Enter. Your browser opens: sign in with your Claude account. Then type `/exit` and press Enter to close Claude again.

## Make a game

### Step 1: choose your game

1. Open the `mystery-forge` folder, then the `configurator` folder.
2. Double-click `index.html`. It opens in your browser. It needs no internet.
3. Choose who plays, how long the game lasts, the language, the kind of story, and what your printer can do.
4. Click **Review and save**, then **Download config**. Your browser saves a small file in your **Downloads** folder.

### Step 2: let the AI make it

1. Open a terminal **inside the `generator` folder**:
   - **Windows:** open the `mystery-forge` folder, then the `generator` folder. Click the address bar at the top of the window, type `powershell`, and press Enter.
   - **macOS:** open the `mystery-forge` folder in Finder. Right-click the `generator` folder and choose **New Terminal at Folder**. (If you do not see it, it is under **Services**.)
2. Type `claude` and press Enter.
3. The first time, Claude asks whether you trust this folder. Choose **Yes**.
4. Type **create a game** and press Enter.
5. The AI shows a summary of your choices and asks you to confirm. Then it asks you to pick one of three story ideas.
6. After that, it works alone for about 1 to 2 hours. You can leave the computer on and do something else.

When it finishes, the AI tells you where the game is: a new folder in `Mystery Forge` on your **Desktop**.

### Step 3: print and play

Open the file whose name starts with `1 -` (the manual). It has the printing checklist, how to prepare the envelopes, and the rules. Read it before you print.

## What you get

A folder on your Desktop (`Mystery Forge/<game title>`) with:

| File                                     | What it is                                                                                                                                                                                               |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `1 - START HERE (manual).pdf`            | Read this first: what to print, how to set up the envelopes, and how to play.                                                                                                                            |
| `2 - PRINT THIS (game materials).pdf`    | The game itself: letters, reports, maps, codes, and puzzles, split into envelopes by "STOP" pages, plus the answer list and the accusation form.                                                         |
| `Game companion.html`                    | An optional page for a phone or a computer. It checks your answers, shows a bit of story for each solved puzzle, gives one hint at a time, keeps the time, and scores your accusation. It works offline. |
| `HOST ONLY - spoilers/3 - Hints.pdf`     | Fold-over hint cards, for groups that play without a phone or computer.                                                                                                                                  |
| `HOST ONLY - spoilers/4 - Solutions.pdf` | Every answer and the full story. Do not open it if you want to play.                                                                                                                                     |

The file names follow the game language. A Spanish game, for example, starts with `1 - EMPIEZA AQUÍ (manual).pdf`.

## Printing tips

- Print at **actual size (100%)**, on one side of the paper. "Fit to page" breaks grids and cut-out pieces. In Chrome or Edge, click **More settings** in the Print window, then choose **Actual size** under **Scale**. In Adobe Reader, click **Actual size** under **Page Sizing & Handling**.
- **Black and white is fine.** Choose it on the configurator page, and the game uses patterns instead of colors.
- **Envelopes:** split the printed stack at each **STOP** page without reading ahead, and put each part in its own envelope (or fold it and use a clip).

## Change a game, or continue a stopped one

- **To change a finished game**, open Claude in the `generator` folder again (see Step 2) and say what you want, for example "make the second puzzle easier" or "print it in black and white".
- **If the AI stopped halfway** (for example because your plan's usage limit was reached), wait until your plan allows more use, open Claude in the `generator` folder again, and type **continue**.

## Languages

A game can be in any of 50 languages, from Afrikaans to Chinese. The AI writes the story and the puzzles in that language.

- **English, Spanish, Catalan, French, German, Italian, and Portuguese** have hand-checked texts for the manual, the labels, and the companion page. For other languages, the AI translates those texts for each game.
- **Japanese, Russian, Arabic, and other languages that do not use the letters A to Z** get fewer kinds of puzzles, because some puzzles (such as letter codes and Morse code) only work with A to Z.
- **Arabic, Hebrew, Persian, and Urdu** pages read from right to left.

## Troubleshooting

| Problem                                             | What to do                                                                                                       |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| The terminal says `claude` or `uv` is not found     | Close the terminal and open a new one. If it still fails, run the install command again.                         |
| The configurator page looks empty                   | Keep the whole `configurator` folder together. The page needs the other files next to it.                        |
| The AI says it found no game settings               | Save your choices on the configurator page first (Step 1), or tell the AI where the file is.                     |
| The AI asks for permission for every step           | Close it and open the terminal inside the `generator` folder itself (Step 2), not in the `mystery-forge` folder. |
| "No browser found"                                  | Install Google Chrome or Microsoft Edge, or let the AI install a small browser for you when it asks.             |
| The AI stopped before the game was ready            | Open Claude in the `generator` folder again and type **continue**.                                               |
| Chinese, Japanese, or Arabic letters print as boxes | Your computer lacks a font for that script. Windows and macOS have them; on Linux, install the Noto fonts.       |

## How the games stay correct

AI can make mistakes, so Mystery Forge never trusts the AI to check its own puzzles:

- **Code builds the puzzles** that code can build (codes, grids, mazes, logic puzzles, locks), so they are correct by construction, and the printed pages are read back and checked.
- **Code checks the whole game:** every clue comes from a real document, no answer shows up too early, every innocent suspect can be cleared, and the game fits the time that you chose.
- **AI test players** get only what real players have and try to solve each puzzle. A puzzle that is too hard, or that has two good answers, goes back for a fix. Another group tries to name the culprit without solving any puzzle: if they can, the story goes back for a fix, because the puzzles must matter.

## For developers

The project is built and maintained with AI agents. The development map is in `AGENTS.md`.

```bash
npm install
npm run check
```

`npm run check` runs every check that CI runs: the JavaScript format, types, and tests, the Python toolkit format, lint, types, and tests (100% coverage), and the generator skill tests.

## License

MIT. See `LICENSE`. The bundled fonts keep their own open licenses, in `toolkit/src/mystery_forge/render/fonts/LICENSES/`.
