# stgzbot

stgzbot is a Windows desktop chat bot for Last Z. It reads the visible game chat using OCR and interacts with chat through mouse and keyboard input. It can host multiple-choice trivia, answer a few fixed commands, and have short AI-assisted conversations.

This project is an independent community tool and is not affiliated with or endorsed by the game publisher. Use it only where automated interaction is allowed, and follow the game's rules.

## Features

- Starts a five-question trivia round when a player uses `stgzbot start trivia [topic]`.
- Accepts A/B/C/D or an exact answer-option text, with one try per player.
- Supports fixed commands: `stgzbot help`, `stgzbot owner`, and `stgzbot info`.
- Answers `stgzbot who's the goat?` with a fixed response.
- Can chat with players addressed by the bot name. Rare unsolicited quips are limited to idle mode.
- Uses RapidOCR locally to read the visible chat; Gemini is used for generated trivia and AI chat.
- Checks that the configured game window is focused before sending chat, and supports the PyAutoGUI corner fail-safe.

## Requirements

- Windows
- Python 3.11 or later
- A game window whose title and chat layout can be configured
- A Gemini API key for AI chat and generated trivia

OCR, screen capture, and desktop input run locally. AI requests send the relevant player message or trivia topic to Google's Gemini API. Review the provider's terms and privacy policy before enabling AI features.

## Setup

Open PowerShell in the project directory:

```powershell
cd path\to\stgzbot_v4
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item config.example.json config.json
```

If PowerShell blocks virtual-environment activation, either adjust the execution policy for your user, or use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Edit `config.json` locally:

1. Set `window_title` to the exact game window title.
2. Set `bot_name`, `call_name`, and `my_name` to match the bot's in-game name.
3. Set `owner_text` and `info_text` as desired.
4. Keep the game window at the resolution you plan to use.

Then run calibration with the game open and the desired chat tab visible:

```powershell
python calibrate.py
```

Select the chat message area, chat input, and send button when prompted. Calibration writes the coordinates to `config.json` and creates `screen.png` for local reference; the screenshot is ignored by Git.

## Gemini API key

The key is read from the `GEMINI_API_KEY` environment variable; it should never be put in `config.json`, source code, or a committed `.env` file. Obtain a key through Google AI Studio and set it for the current PowerShell session using a hidden prompt:

```powershell
$secret = Read-Host "Gemini API key" -AsSecureString
$env:GEMINI_API_KEY = [Net.NetworkCredential]::new("", $secret).Password
```

This setting lasts only for that PowerShell session. Start the bot from the same session. Do not paste the real key into a command that will be saved in shell history or into a screenshot. Revoke and replace the key immediately if it is ever exposed.

## Run

With the virtual environment active, the game open, and `GEMINI_API_KEY` set:

```powershell
python bot.py
```

The bot waits through the configured countdown before starting. Stop it with Ctrl+C or move the mouse to a screen corner to activate the fail-safe. Keep the game window visible and at the calibrated size.

## Diagnostics and test modes

Run these from the project directory:

```powershell
python bot.py --demo
python bot.py --test-guard "text to check"
python bot.py --test-ai science
python bot.py --test-ocr --raw
python bot.py --test-send "Test message"
```

- `--demo` prints sample messages without interacting with the game.
- `--test-guard` checks how text is classified and sanitized.
- `--test-ai` makes live Gemini calls.
- `--test-ocr` captures and OCRs the configured chat area; `--raw` includes OCR rows.
- `--test-send` types into the game chat. Use it only after verifying calibration and focus.

## Configuration and privacy

- `config.json` is local and ignored by Git. It contains your game window title, account names, and screen coordinates.
- `screen.png`, `debug_crop.png`, and other debug screenshots are ignored. They may contain private chat or desktop information; inspect them before sharing.
- `.env` files, Python environments, and bytecode caches are ignored.
- The repository includes `config.example.json` as a sanitized starting point. Copy it to `config.json` and configure it locally.
- Do not commit API keys, tokens, private screenshots, or personal account details. Check `git status` and inspect staged changes before pushing.

## Upload to GitHub

Create an empty repository on GitHub (do not initialize it with a README if you plan to push this README). Then, from PowerShell:

```powershell
cd path\to\stgzbot_v4
git init
git add README.md .gitignore config.example.json bot.py calibrate.py common.py guard.py llm.py requirements.txt
git status
git diff --cached
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Review both `git status` and `git diff --cached` before committing. The ignored local `config.json` and screenshots should not appear in the staged file list. If a secret was committed previously, deleting it in a later commit is not enough: revoke it and remove it from Git history before publishing.
