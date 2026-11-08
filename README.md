# Bot AI

This repository contains a simple Discord bot.

Prerequisites
- Python 3.11 installed
- pipenv (optional, recommended)

Setup (pipenv)
```bash
pipenv --rm || true
pipenv install --python 3.11
pipenv shell
pipenv install
```

Run

Temporarily set the token for the current shell and run the bot:

PowerShell:
```powershell
$env:DISCORD_TOKEN="your_token_here"
python bot.py
```

Command Prompt:
```cmd
set DISCORD_TOKEN=your_token_here
python bot.py
```

Or set `DISCORD_TOKEN` persistently with `setx` (new shell required).

Security
- The bot reads the Discord token from the `DISCORD_TOKEN` environment variable. Do not hard-code tokens in source.

If you'd like, I can (1) recreate the pipenv virtualenv and run `python bot.py`, or (2) perform a deeper secrets scan. Which would you like next?