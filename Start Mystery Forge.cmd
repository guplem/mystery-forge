@echo off
rem Double-click this file to make a mystery game. It installs uv and Claude Code the first time,
rem then starts the AI in the generator folder. Keep it in the mystery-forge folder.
setlocal
chcp 65001 >nul
title Mystery Forge
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo.
echo   MYSTERY FORGE
echo   =============
echo.

where uv >nul 2>nul
if errorlevel 1 (
  echo   Installing uv, one time only. This takes about a minute...
  powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
where claude >nul 2>nul
if errorlevel 1 (
  echo   Installing Claude Code, one time only. This takes about a minute...
  powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://claude.ai/install.ps1 | iex"
)
where claude >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Claude Code could not be installed. See "Install by hand" in README.md.
  pause
  exit /b 1
)

echo.
echo   What do you want to do?
echo.
echo     1  Choose a new game      (opens the settings page in your browser)
echo     2  Make the game          (the AI writes it: about 1 to 2 hours)
echo     3  Continue a stopped game
echo     4  Talk to the AI         (for example, to change a finished game)
echo.
choice /c 1234 /n /m "  Type 1, 2, 3, or 4: "
if errorlevel 4 goto talk
if errorlevel 3 goto continue
if errorlevel 2 goto make

start "" "%~dp0configurator\index.html"
echo.
echo   The settings page is open in your browser.
echo   Choose your game, click "Review and save", then "Download config".
echo   Then come back to this window.
echo.
pause

:make
echo.
echo   Starting the AI. The first time, sign in with your Claude account,
echo   and answer "Yes" when it asks whether you trust this folder.
echo.
cd /d "%~dp0generator"
claude "create a game"
goto done

:continue
cd /d "%~dp0generator"
claude "continue"
goto done

:talk
cd /d "%~dp0generator"
claude

:done
endlocal
