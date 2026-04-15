# CanvasScraper

## What this is
A Python CLI tool that scrapes course materials from Canvas LMS and uploads them to Google Drive, mirroring the Canvas module folder structure.

## Target users
MBA students at UW (and potentially other schools). Must be runnable by non-technical users who can follow a README.

## Tech stack
- Python 3.10+
- `requests` for Canvas API
- `google-api-python-client` + `google-auth-oauthlib` for Google Drive
- `python-dotenv` for config
- No web framework — pure CLI with `input()` prompts

## Project structure
```
canvas_scraper/
  __init__.py
  cli.py              # Entry point (console script: canvas-scraper)
  config.py           # .env loading, config dataclass
  canvas_client.py    # Canvas LMS API wrapper
  drive_client.py     # Google Drive OAuth + upload
  scraper.py          # Orchestrator
```

## Key conventions
- Keep the codebase small — under 800 lines total
- Each module has a single responsibility
- No unnecessary abstractions or premature generalization
- Use plain `input()` for interactive prompts, not click/argparse (unless adding flags later)
- Secrets go in `.env` (gitignored), Google OAuth credentials in `credentials/` (gitignored)

## Canvas API
- Base URL: configurable, default `https://canvas.uw.edu`
- Auth: Bearer token from user's Canvas settings
- Pagination: follow `Link` header `rel="next"`
- Rate limiting: check `X-Rate-Limit-Remaining`, sleep if low

## Google Drive API
- OAuth2 "Desktop app" flow with `drive.file` scope
- Token cached in `credentials/token.json`
- Folder creation is idempotent (check-before-create)
- File upload is idempotent (check-before-upload via manifest)

## Running
```bash
pip install -e .
cp .env.example .env  # fill in CANVAS_API_TOKEN
# place client_secret.json in credentials/
canvas-scraper
```

## Dev commands
```bash
pip install -e .          # install in editable mode
python -m canvas_scraper.cli  # alternative way to run
```
