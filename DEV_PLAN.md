# Development Plan

## Overview
Build a Python CLI tool that scrapes Canvas LMS course materials and uploads them to Google Drive.

**Content to scrape:** Files/documents, assignment submissions (user's own), syllabus
**Organization:** Mirror Canvas module structure as Drive folders
**Auth:** Canvas API token + Google OAuth (Workspace/school accounts)

## Tasks

### Task 1: Project scaffolding + config
- [ ] `pyproject.toml` with dependencies and `canvas-scraper` console script
- [ ] `canvas_scraper/config.py` — load `.env`, return config dataclass
- [ ] `.env.example` with `CANVAS_API_TOKEN`, `CANVAS_BASE_URL`
- [ ] Update `.gitignore` for `credentials/`, `.env`, `token.json`

### Task 2: Canvas client — auth + courses
- [ ] `CanvasClient` class with Bearer auth
- [ ] Auto-pagination via Link headers (generator)
- [ ] Rate-limit awareness (`X-Rate-Limit-Remaining`)
- [ ] `get_courses()` — active enrollments only

### Task 3: Canvas client — content endpoints
- [ ] `get_modules()`, `get_module_items()`
- [ ] `get_file()`, `download_file()` (streaming to disk)
- [ ] `get_assignments()`, `get_my_submissions()`
- [ ] `get_syllabus()` via `include[]=syllabus_body`

### Task 4: Drive client — OAuth + folders
- [ ] `authenticate()` — OAuth Desktop flow, token caching
- [ ] `create_folder()` — idempotent
- [ ] `create_folder_tree()` — nested folder creation

### Task 5: Drive client — file upload
- [ ] `upload_file()` — resumable, idempotent
- [ ] `upload_html_as_doc()` — syllabus as Google Doc

### Task 6: Scraper orchestrator
- [ ] `scrape_course()` — course folder → syllabus → modules → assignments
- [ ] JSON manifest for tracking progress / enabling re-runs
- [ ] Error handling: log + skip + continue

### Task 7: CLI interface
- [ ] `main()` — config → Canvas auth → Google auth → course picker → scrape → summary
- [ ] Interactive course selection with numbered list

### Task 8: README + polish
- [ ] Setup instructions for classmates
- [ ] Google Cloud project setup guide
- [ ] `--dry-run` flag
- [ ] Common error messages / troubleshooting

## Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Config | `.env` + `python-dotenv` | Simplest portable approach, no YAML needed |
| Canvas auth | API token | Standard, well-documented, no SSO complexity |
| Drive auth | OAuth Desktop + `drive.file` scope | Files go to user's own Drive, minimal permissions |
| Drive scope | `drive.file` | Only sees files the app created — safer, easier approval |
| Idempotency | JSON manifest | Human-readable, no DB dependency, sufficient for this scale |
| CLI framework | Plain `input()` | Zero extra deps, interaction is sequential |
| File downloads | Stream to disk, then upload | Handles large files, compatible with resumable upload |
| Google Cloud sharing | "Testing" mode + test users | Supports up to 100 users, no verification needed |
