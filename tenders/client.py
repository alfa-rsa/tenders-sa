"""API client for the SA Government eTenders OCDS API."""

import os
import time
from typing import Optional

import httpx

BASE_URL = os.getenv("ETENDERS_BASE_URL", "https://ocds-api.etenders.gov.za")
TIMEOUT = float(os.getenv("ETENDERS_TIMEOUT", "120"))


class TenderClient:
    """Low-level API client. Handles retries and rate limiting."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = TIMEOUT,
        rate_limit: float = 0.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit = rate_limit  # seconds between requests
        self._last_request: float = 0

    def _rate_limit(self) -> None:
        """Enforce rate limit between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def fetch_releases(
        self,
        date_from: str,
        date_to: str,
        page_number: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        Fetch releases from the eTenders OCDS API.

        Note: status, category, buyer filters are silently ignored by the API.
        All filtering happens in SQLite after fetching.

        Args:
            date_from: Start date YYYY-MM-DD
            date_to: End date YYYY-MM-DD
            page_number: 1-indexed page number
            page_size: Results per page (max ~100)

        Returns:
            API response dict with 'releases' list and pagination fields
        """
        self._rate_limit()

        params = {
            "PageNumber": page_number,
            "PageSize": page_size,
            "dateFrom": date_from,
            "dateTo": date_to,
        }

        url = f"{self.base_url}/api/OCDSReleases"
        last_error = None

        for attempt in range(3):
            try:
                resp = httpx.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers={
                        "User-Agent": "tenders-sa/0.1.0",
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as e:
                last_error = f"timeout after {self.timeout}s (attempt {attempt+1}/3)"
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                if e.response.status_code in (500, 502, 503, 504):
                    if attempt < 2:
                        time.sleep(10 * (attempt + 1))
                    else:
                        raise
                else:
                    raise
            except httpx.RequestError as e:
                last_error = str(e)
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                else:
                    raise

        raise RuntimeError(f"Failed after 3 attempts: {last_error}")

    def fetch_all_pages(
        self,
        date_from: str,
        date_to: str,
        page_size: int = 50,
        max_pages: Optional[int] = None,
        progress_callback=None,
    ) -> list[dict]:
        """
        Fetch all pages for a date range.

        Args:
            date_from: Start date
            date_to: End date
            page_size: Results per page
            max_pages: Cap on pages (None = until API says done)
            progress_callback: fn(page_num, total_estimate) called each page

        Returns:
            List of all release dicts
        """
        all_releases = []
        page = 1

        while True:
            data = self.fetch_releases(
                date_from=date_from,
                date_to=date_to,
                page_number=page,
                page_size=page_size,
            )
            releases = data.get("releases", [])
            all_releases.extend(releases)

            if progress_callback:
                progress_callback(page, None)

            # Stop conditions
            if not releases:
                break
            if max_pages and page >= max_pages:
                break
            if len(releases) < page_size:
                break

            page += 1

        return all_releases
