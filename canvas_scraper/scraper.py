"""Orchestrator: ties Canvas download to Google Drive upload."""

import json
import re
import tempfile
from pathlib import Path

from canvas_scraper import canvas_client as cc
from canvas_scraper import drive_client as dc


def _safe_name(name: str) -> str:
    """Strip characters that cause issues in Drive folder/file names."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def _extract_canvas_file_ids(html: str) -> list[int]:
    """
    Parse Canvas page HTML and return unique file IDs for all Canvas-hosted files.

    Matches two patterns found in Canvas page bodies:
      - data-api-endpoint="https://canvas.example.edu/api/v1/courses/N/files/FILE_ID"
      - href="https://canvas.example.edu/courses/N/files/FILE_ID[/...]"
    """
    file_ids: list[int] = []
    seen: set[int] = set()

    # Prefer the data-api-endpoint attribute — most reliable
    for m in re.finditer(r'data-api-endpoint="[^"]+/api/v1/(?:courses/\d+/)?files/(\d+)"', html):
        fid = int(m.group(1))
        if fid not in seen:
            seen.add(fid)
            file_ids.append(fid)

    # Fall back to href patterns: /courses/N/files/FILE_ID or /files/FILE_ID
    for m in re.finditer(r'href="[^"]+/(?:courses/\d+/)?files/(\d+)', html):
        fid = int(m.group(1))
        if fid not in seen:
            seen.add(fid)
            file_ids.append(fid)

    return file_ids


def _load_manifest(manifest_path: Path) -> dict:
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {}


def _save_manifest(manifest_path: Path, manifest: dict) -> None:
    manifest_path.write_text(json.dumps(manifest, indent=2))


def scrape_courses(
    canvas: cc.CanvasClient,
    drive,
    courses: list[dict],
    drive_root_id: str,
    manifest_path: Path,
    dry_run: bool = False,
) -> dict:
    """Scrape a list of courses. Returns summary dict with counts and failures."""
    manifest = _load_manifest(manifest_path)
    summary = {"uploaded": 0, "skipped": 0, "failed": []}

    for course in courses:
        course_id = course["id"]
        course_name = _safe_name(course["name"])
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Scraping: {course_name}")

        try:
            _scrape_course(
                canvas, drive, course_id, course_name,
                drive_root_id, manifest, manifest_path, dry_run, summary,
            )
        except Exception as e:
            print(f"  ERROR: course-level failure — {e}")
            summary["failed"].append({"course": course_name, "error": str(e)})

    return summary


def _scrape_course(
    canvas: cc.CanvasClient,
    drive,
    course_id: int,
    course_name: str,
    drive_root_id: str,
    manifest: dict,
    manifest_path: Path,
    dry_run: bool,
    summary: dict,
) -> None:
    course_key = str(course_id)
    if course_key not in manifest:
        manifest[course_key] = {}

    if not dry_run:
        course_folder_id = dc.create_folder(drive, course_name, drive_root_id)
    else:
        course_folder_id = "dry-run"

    # --- Syllabus ---
    try:
        syllabus_html = canvas.get_syllabus(course_id)
        if syllabus_html:
            _handle_item(
                drive, course_folder_id, "Syllabus",
                html_content=syllabus_html,
                key=f"{course_key}:syllabus",
                manifest=manifest, manifest_path=manifest_path,
                dry_run=dry_run, summary=summary,
            )
    except Exception as e:
        print(f"  WARNING: could not fetch syllabus — {e}")
        summary["failed"].append({"course": course_name, "item": "syllabus", "error": str(e)})

    # --- Modules ---
    try:
        modules = canvas.get_modules(course_id)
    except Exception as e:
        print(f"  WARNING: could not fetch modules — {e}")
        modules = []

    for module in modules:
        module_name = _safe_name(module["name"])
        print(f"  Module: {module_name}")

        if not dry_run:
            module_folder_id = dc.create_folder(drive, module_name, course_folder_id)
        else:
            module_folder_id = "dry-run"

        try:
            items = canvas.get_module_items(course_id, module["id"])
        except Exception as e:
            print(f"    WARNING: could not fetch module items — {e}")
            continue

        for item in items:
            item_type = item.get("type")
            item_title = _safe_name(item.get("title", "untitled"))
            item_key = f"{course_key}:module:{module['id']}:item:{item['id']}"

            if item_type == "File":
                try:
                    file_meta = canvas.get_file(item["content_id"])
                    download_url = file_meta.get("url")
                    filename = _safe_name(file_meta.get("display_name", item_title))
                    if download_url:
                        _handle_item(
                            drive, module_folder_id, filename,
                            download_url=download_url, canvas=canvas,
                            key=item_key, manifest=manifest, manifest_path=manifest_path,
                            dry_run=dry_run, summary=summary,
                        )
                except Exception as e:
                    print(f"    WARNING: {item_title} — {e}")
                    summary["failed"].append({"course": course_name, "item": item_title, "error": str(e)})
            elif item_type == "Page":
                page_url_slug = item.get("page_url")
                if not page_url_slug:
                    continue
                try:
                    page = canvas.get_page(course_id, page_url_slug)
                    body = page.get("body") or ""
                    file_ids = _extract_canvas_file_ids(body)
                    if not file_ids:
                        continue
                    print(f"    Page '{item_title}': found {len(file_ids)} linked file(s)")
                    for file_id in file_ids:
                        file_key = f"{course_key}:module:{module['id']}:page_file:{file_id}"
                        try:
                            file_meta = canvas.get_file(file_id)
                            download_url = file_meta.get("url")
                            filename = _safe_name(file_meta.get("display_name", str(file_id)))
                            if download_url:
                                _handle_item(
                                    drive, module_folder_id, filename,
                                    download_url=download_url, canvas=canvas,
                                    key=file_key, manifest=manifest, manifest_path=manifest_path,
                                    dry_run=dry_run, summary=summary,
                                )
                        except Exception as e:
                            print(f"    WARNING: file {file_id} from page '{item_title}' — {e}")
                            summary["failed"].append({"course": course_name, "item": f"{item_title}/file:{file_id}", "error": str(e)})
                except Exception as e:
                    print(f"    WARNING: page '{item_title}' — {e}")
                    summary["failed"].append({"course": course_name, "item": item_title, "error": str(e)})
            else:
                # Skip assignments, external URLs, etc. — handled separately or not applicable
                pass

    # --- Assignments + Submissions ---
    try:
        assignments = canvas.get_assignments(course_id)
        submissions = canvas.get_my_submissions(course_id)
        sub_by_assignment = {str(s["assignment_id"]): s for s in submissions}
    except Exception as e:
        print(f"  WARNING: could not fetch assignments — {e}")
        assignments = []
        sub_by_assignment = {}

    if assignments:
        if not dry_run:
            assign_folder_id = dc.create_folder(drive, "Assignments", course_folder_id)
        else:
            assign_folder_id = "dry-run"

        for assignment in assignments:
            a_id = str(assignment["id"])
            a_name = _safe_name(assignment.get("name", f"assignment_{a_id}"))
            submission = sub_by_assignment.get(a_id)

            if not submission:
                continue

            attachments = submission.get("attachments", [])
            for att in attachments:
                filename = _safe_name(att.get("display_name", att.get("filename", "file")))
                download_url = att.get("url")
                item_key = f"{course_key}:submission:{a_id}:att:{att['id']}"
                if download_url:
                    _handle_item(
                        drive, assign_folder_id, f"{a_name} — {filename}",
                        download_url=download_url, canvas=canvas,
                        key=item_key, manifest=manifest, manifest_path=manifest_path,
                        dry_run=dry_run, summary=summary,
                    )


def _handle_item(
    drive,
    folder_id: str,
    name: str,
    *,
    html_content: str = None,
    download_url: str = None,
    canvas: cc.CanvasClient = None,
    key: str,
    manifest: dict,
    manifest_path: Path,
    dry_run: bool,
    summary: dict,
) -> None:
    """Upload a single item (file or HTML doc) to Drive, tracking via manifest."""
    if key in manifest:
        print(f"    SKIP (already uploaded): {name}")
        summary["skipped"] += 1
        return

    if dry_run:
        print(f"    [DRY RUN] would upload: {name}")
        summary["uploaded"] += 1
        return

    try:
        if html_content is not None:
            file_id = dc.upload_html_as_doc(drive, html_content, folder_id, name)
        else:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            canvas.download_file(download_url, tmp_path)
            file_id = dc.upload_file(drive, tmp_path, folder_id, name)
            tmp_path.unlink(missing_ok=True)

        manifest[key] = file_id
        _save_manifest(manifest_path, manifest)
        print(f"    OK: {name}")
        summary["uploaded"] += 1
    except Exception as e:
        print(f"    ERROR: {name} — {e}")
        summary["failed"].append({"item": name, "error": str(e)})
