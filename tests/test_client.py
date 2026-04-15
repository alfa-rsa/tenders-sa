"""Tests for TenderClient HTTP API client."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from tenders.client import TenderClient


def make_mock_response(json_data, status_code=200):
    """Build a simple mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


class TestTenderClient:
    def test_fetch_releases_basic(self):
        client = TenderClient()
        with patch("httpx.get") as mock_get:
            mock_get.return_value = make_mock_response({
                "releases": [
                    {"ocid": "ocds-1", "tender": {"title": "Tender 1"}},
                    {"ocid": "ocds-2", "tender": {"title": "Tender 2"}},
                ]
            })

            result = client.fetch_releases("2026-04-01", "2026-04-15")

            assert len(result["releases"]) == 2
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "OCDSReleases" in call_args.args[0]
            assert call_args.kwargs["params"]["dateFrom"] == "2026-04-01"
            assert call_args.kwargs["params"]["PageNumber"] == 1

    def test_fetch_releases_pagination(self):
        client = TenderClient()
        with patch("httpx.get") as mock_get:
            mock_get.return_value = make_mock_response({
                "releases": [{"ocid": f"ocds-{i}", "tender": {"title": f"Tender {i}"}} for i in range(50)],
            })

            result = client.fetch_releases("2026-04-01", "2026-04-15", page_size=50)
            assert len(result["releases"]) == 50

    def test_fetch_releases_timeout_retries(self):
        client = TenderClient()
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                make_mock_response({"releases": [{"ocid": "ocds-1", "tender": {}}]}),
            ]

            result = client.fetch_releases("2026-04-01", "2026-04-15")
            assert len(result["releases"]) == 1
            assert mock_get.call_count == 3

    def test_fetch_releases_500_retries_then_raises(self):
        client = TenderClient()
        with patch("httpx.get") as mock_get:
            mock_get.return_value = make_mock_response({}, status_code=500)
            with pytest.raises(httpx.HTTPStatusError):
                client.fetch_releases("2026-04-01", "2026-04-15")
            # 1 initial + 2 retries = 3
            assert mock_get.call_count == 3

    def test_fetch_releases_400_raises_immediately(self):
        client = TenderClient()
        with patch("httpx.get") as mock_get:
            mock_get.return_value = make_mock_response({}, status_code=400)
            with pytest.raises(httpx.HTTPStatusError):
                client.fetch_releases("2026-04-01", "2026-04-15")
            assert mock_get.call_count == 1

    def test_fetch_all_pages_stops_on_empty(self):
        client = TenderClient()
        with patch.object(client, "fetch_releases") as mock_fetch:
            mock_fetch.return_value = {"releases": [{"ocid": "ocds-1", "tender": {}}]}

            releases = client.fetch_all_pages("2026-04-01", "2026-04-15")
            assert len(releases) == 1
            assert mock_fetch.call_count == 1

    def test_fetch_all_pages_respects_max_pages(self):
        """When a full page is returned, max_pages caps how many pages are fetched."""
        client = TenderClient()
        with patch.object(client, "fetch_releases") as mock_fetch:
            # Return a full page (50 items) every time — so it never hits the
            # "short page" break condition, only max_pages
            mock_fetch.return_value = {
                "releases": [{"ocid": f"ocds-{i}", "tender": {}} for i in range(50)]
            }

            releases = client.fetch_all_pages("2026-04-01", "2026-04-15", max_pages=3)
            assert mock_fetch.call_count == 3
            assert len(releases) == 150  # 3 pages x 50

    def test_fetch_all_pages_stops_when_page_under_page_size(self):
        client = TenderClient()
        with patch.object(client, "fetch_releases") as mock_fetch:
            mock_fetch.side_effect = [
                {"releases": [{"ocid": f"ocds-{i}", "tender": {}} for i in range(50)]},
                {"releases": [{"ocid": "ocds-last", "tender": {}}]},
            ]

            releases = client.fetch_all_pages("2026-04-01", "2026-04-15")
            assert len(releases) == 51
            assert mock_fetch.call_count == 2

    def test_rate_limit_enforced(self):
        client = TenderClient(rate_limit=0.5)
        with patch("httpx.get") as mock_get:
            mock_get.return_value = make_mock_response({"releases": []})
            import time
            start = time.time()
            client.fetch_releases("2026-04-01", "2026-04-15")
            client.fetch_releases("2026-04-01", "2026-04-15")
            elapsed = time.time() - start
            assert elapsed >= 0.4  # at least one rate_limit interval

    def test_custom_base_url(self):
        client = TenderClient(base_url="https://custom.api.example.com")
        with patch("httpx.get") as mock_get:
            mock_get.return_value = make_mock_response({"releases": []})
            client.fetch_releases("2026-04-01", "2026-04-15")
            assert "custom.api.example.com" in mock_get.call_args.args[0]
