#!/bin/bash
# Double-click this file to make a mystery game. It installs uv and Claude Code the first time,
# then starts the AI in the generator folder. Keep it in the mystery-forge folder.
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
export PATH="$HOME/.local/bin:$PATH"

echo
echo "  MYSTERY FORGE"
echo "  ============="
echo

if ! command -v uv >/dev/null 2>&1; then
  echo "  Installing uv, one time only. This takes about a minute..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "  Installing Claude Code, one time only. This takes about a minute..."
  curl -fsSL https://claude.ai/install.sh | bash
fi
export PATH="$HOME/.local/bin:$PATH"
if ! command -v claude >/dev/null 2>&1; then
  echo
  echo "  Claude Code could not be installed. See \"Install by hand\" in README.md."
  read -r -p "  Press Enter to close this window."
  exit 1
fi

echo
echo "  What do you want to do?"
echo
echo "    1  Choose a new game      (opens the settings page in your browser)"
echo "    2  Make the game          (the AI writes it: about 1 to 2 hours)"
echo "    3  Continue a stopped game"
echo "    4  Talk to the AI         (for example, to change a finished game)"
echo
read -r -p "  Type 1, 2, 3, or 4, then press Enter: " CHOICE

if [ "$CHOICE" = "4" ]; then
  cd "$ROOT/generator" || exit 1
  exec claude
fi

if [ "$CHOICE" = "3" ]; then
  cd "$ROOT/generator" || exit 1
  exec claude "continue"
fi

if [ "$CHOICE" = "1" ]; then
  open "$ROOT/configurator/index.html"
  echo
  echo "  The settings page is open in your browser."
  echo "  Choose your game, click \"Review and save\", then \"Download config\"."
  read -r -p "  Then come back to this window and press Enter."
fi

echo
echo "  Starting the AI. The first time, sign in with your Claude account,"
echo "  and answer \"Yes\" when it asks whether you trust this folder."
echo
cd "$ROOT/generator" || exit 1
exec claude "create a game"
