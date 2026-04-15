"""Canvas LMS API client."""

import time
from typing import Generator

import requests


class CanvasAuthError(Exception):
    pass


class CanvasClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_token}"})

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/api/v1{endpoint}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code == 401:
            raise CanvasAuthError(
                "Canvas API token is invalid or expired.\n"
                "Generate a new one at: Canvas > Account > Settings > Approved Integrations"
            )
        resp.raise_for_status()
        return resp

    def _paginate(self, endpoint: str, params: dict = None) -> Generator[dict, None, None]:
        """Yield items across all pages, following Link headers."""
        params = {**(params or {}), "per_page": 100}
        url = f"{self.base_url}/api/v1{endpoint}"

        while url:
            resp = self.session.get(url, params=params)
            if resp.status_code == 401:
                raise CanvasAuthError(
                    "Canvas API token is invalid or expired.\n"
                    "Generate a new one at: Canvas > Account > Settings > Approved Integrations"
                )
            resp.raise_for_status()

            # Rate limit awareness
            remaining = resp.headers.get("X-Rate-Limit-Remaining")
            if remaining and float(remaining) < 50:
                time.sleep(1)

            yield from resp.json()

            # Follow Link header for next page
            links = _parse_link_header(resp.headers.get("Link", ""))
            url = links.get("next")
            params = {}  # params are already encoded in the next URL

    def validate_token(self) -> dict:
        """Validate token by fetching the current user. Returns user dict."""
        return self._request("GET", "/users/self").json()

    def get_courses(self) -> list[dict]:
        """Return all active courses the user is enrolled in."""
        courses = list(
            self._paginate(
                "/courses",
                params={"enrollment_state": "active", "include[]": "term"},
            )
        )
        # Filter out courses with no name (sometimes returned for deleted/pending courses)
        return [c for c in courses if c.get("name")]

    def get_modules(self, course_id: int) -> list[dict]:
        """Return all modules for a course."""
        return list(self._paginate(f"/courses/{course_id}/modules"))

    def get_module_items(self, course_id: int, module_id: int) -> list[dict]:
        """Return all items within a module."""
        return list(
            self._paginate(
                f"/courses/{course_id}/modules/{module_id}/items",
                params={"include[]": "content_details"},
            )
        )

    def get_file(self, file_id: int) -> dict:
        """Return file metadata including download URL."""
        return self._request("GET", f"/files/{file_id}").json()

    def download_file(self, url: str, dest_path) -> None:
        """Stream download a file (Canvas pre-signed URL) to dest_path."""
        with self.session.get(url, stream=True, allow_redirects=True) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

    def get_assignments(self, course_id: int) -> list[dict]:
        """Return all assignments for a course."""
        return list(self._paginate(f"/courses/{course_id}/assignments"))

    def get_my_submissions(self, course_id: int) -> list[dict]:
        """Return the current user's submissions for all assignments in a course."""
        return list(
            self._paginate(
                f"/courses/{course_id}/students/submissions",
                params={
                    "student_ids[]": "self",
                    "include[]": "submission_comments",
                },
            )
        )

    def get_syllabus(self, course_id: int) -> str | None:
        """Return syllabus HTML body, or None if not available."""
        data = self._request(
            "GET",
            f"/courses/{course_id}",
            params={"include[]": "syllabus_body"},
        ).json()
        return data.get("syllabus_body")

    def get_page(self, course_id: int, page_url: str) -> dict:
        """Return page data including HTML body."""
        return self._request("GET", f"/courses/{course_id}/pages/{page_url}").json()


def _parse_link_header(header: str) -> dict[str, str]:
    """Parse a Link header into a dict of {rel: url}."""
    links = {}
    if not header:
        return links
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        sections = part.split(";")
        if len(sections) < 2:
            continue
        url = sections[0].strip().strip("<>")
        for attr in sections[1:]:
            attr = attr.strip()
            if attr.startswith("rel="):
                rel = attr[4:].strip('"')
                links[rel] = url
    return links
