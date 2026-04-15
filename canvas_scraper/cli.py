"""CLI entry point for canvas-scraper."""

import argparse
import sys
from pathlib import Path

from canvas_scraper.canvas_client import CanvasClient, CanvasAuthError
from canvas_scraper.config import load_config
from canvas_scraper import drive_client as dc
from canvas_scraper.scraper import scrape_courses


def main():
    parser = argparse.ArgumentParser(
        prog="canvas-scraper",
        description="Scrape Canvas LMS course materials and upload to Google Drive.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be downloaded/uploaded without doing it.",
    )
    args = parser.parse_args()

    print("Canvas -> Google Drive Scraper")
    print("=" * 40)

    # --- Load config ---
    try:
        config = load_config()
    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    # --- Canvas auth ---
    canvas = CanvasClient(config.canvas_base_url, config.canvas_api_token)
    print(f"\nConnecting to Canvas ({config.canvas_base_url})...")
    try:
        user = canvas.validate_token()
        print(f"  Logged in as: {user.get('name', user.get('login_id', 'unknown'))}")
    except CanvasAuthError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Could not reach Canvas — {e}")
        sys.exit(1)

    # --- Google Drive auth ---
    print("\nAuthenticating with Google Drive...")
    print("  (A browser window will open if this is your first time)")
    try:
        drive = dc.authenticate(config.credentials_dir)
        print("  Google Drive: authenticated")
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Google Drive authentication failed — {e}")
        sys.exit(1)

    # --- Fetch and display courses ---
    print("\nFetching your courses...")
    try:
        courses = canvas.get_courses()
    except Exception as e:
        print(f"\nERROR: Could not fetch courses — {e}")
        sys.exit(1)

    if not courses:
        print("No active courses found.")
        sys.exit(0)

    print(f"\nFound {len(courses)} course(s):\n")
    for i, course in enumerate(courses, 1):
        term = course.get("term", {}).get("name", "") if course.get("term") else ""
        term_str = f" [{term}]" if term else ""
        print(f"  {i:2}. {course['name']}{term_str}")

    # --- Course selection ---
    print('\nEnter course numbers to scrape (e.g. "1,3,5"), or "all":')
    selection = input("> ").strip().lower()

    if selection == "all":
        selected_courses = courses
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_courses = [courses[i] for i in indices]
        except (ValueError, IndexError):
            print("ERROR: Invalid selection.")
            sys.exit(1)

    if not selected_courses:
        print("No courses selected.")
        sys.exit(0)

    # --- Drive root folder ---
    default_root = "CanvasScraper"
    print(f'\nGoogle Drive root folder name (press Enter for "{default_root}"):')
    root_name = input("> ").strip() or default_root

    # --- Manifest path ---
    config.credentials_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config.credentials_dir / "manifest.json"

    # --- Create root folder in Drive ---
    if args.dry_run:
        drive_root_id = "dry-run"
        print(f'\n[DRY RUN] Would create/use Drive folder: "{root_name}"')
    else:
        print(f'\nCreating Drive folder "{root_name}"...')
        drive_root_id = dc.create_folder(drive, root_name)
        print(f"  Folder ready (id: {drive_root_id})")

    # --- Scrape ---
    print(f"\nScraping {len(selected_courses)} course(s)...\n")
    summary = scrape_courses(
        canvas=canvas,
        drive=drive,
        courses=selected_courses,
        drive_root_id=drive_root_id,
        manifest_path=manifest_path,
        dry_run=args.dry_run,
    )

    # --- Summary ---
    print("\n" + "=" * 40)
    print("Done!")
    print(f"  Uploaded : {summary['uploaded']}")
    print(f"  Skipped  : {summary['skipped']} (already in Drive)")
    if summary["failed"]:
        print(f"  Failed   : {len(summary['failed'])}")
        for f in summary["failed"]:
            item = f.get("item") or f.get("course", "?")
            print(f"    - {item}: {f['error']}")
    print()
    if not args.dry_run:
        print(f"Files are in your Google Drive under \"{root_name}\".")


if __name__ == "__main__":
    main()
