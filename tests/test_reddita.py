from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from reddita import SourceRequest, SourceResult
from reddita.cli import main
from reddita.contract import RedditContractError, normalize_reddit_request
from reddita.models import CaptureEnvelope, CaptureGap
from reddita.scraper import RedditPage, capture_reddit_pages
from reddita.scraper import allow_browser_request
from reddita.transport import PublicHttpsBoundary, PublicTransportError


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class RedditaTests(unittest.TestCase):
    def test_search_contract_is_canonical_and_bounded(self):
        identity, url = normalize_reddit_request(
            "search", "python tools", {"pageSize": 10, "maxComments": 100},
        )
        self.assertEqual(identity, "python tools")
        self.assertEqual(url, "https://old.reddit.com/search?q=python+tools")
        with self.assertRaises(RedditContractError):
            normalize_reddit_request(
                "search", "python", {"pageSize": 101, "maxComments": 100},
            )

    def test_browser_boundary_is_get_only_and_reddit_only(self):
        self.assertTrue(allow_browser_request(
            "GET", "https://old.reddit.com/r/python/",
            request_count=1, max_requests=10,
        ))
        self.assertFalse(allow_browser_request(
            "POST", "https://old.reddit.com/r/python/",
            request_count=1, max_requests=10,
        ))
        self.assertFalse(allow_browser_request(
            "GET", "https://example.com/r/python/",
            request_count=1, max_requests=10,
        ))
        self.assertFalse(allow_browser_request(
            "GET", "https://old.reddit.com/api/vote",
            request_count=1, max_requests=10,
        ))

    def test_transport_rejects_mixed_public_and_private_dns(self):
        boundary = PublicHttpsBoundary(
            allowed_hosts={"old.reddit.com"},
            resolver=lambda *_args, **_kwargs: [
                (2, 1, 6, "", ("93.184.216.34", 443)),
                (2, 1, 6, "", ("10.0.0.2", 443)),
            ],
        )
        with self.assertRaises(PublicTransportError) as caught:
            boundary.resolve("https://old.reddit.com/r/python/")
        self.assertEqual(caught.exception.code, "mixed-addresses-denied")

    def test_listing_parser_returns_stable_json_record(self):
        request = SourceRequest(
            source="reddit", operation="search", locator="python tools",
            parameters_json='{"maxComments":100,"pageSize":1}',
            max_records=1, max_pages=1,
        )
        capture = capture_reddit_pages(
            request,
            (RedditPage(
                url="https://old.reddit.com/search?q=python+tools",
                html=(
                    '<div class="thing" data-fullname="t3_abc123" '
                    'data-subreddit="python" data-author="alice" data-score="42">'
                    '<a class="title" href="https://example.test/article">First post</a>'
                    '<a class="comments" href="/r/python/comments/abc123/post/">12 comments</a>'
                    '</div>'
                ),
            ),),
            captured_at=NOW,
        )
        self.assertTrue(capture.result.envelope.complete)
        self.assertEqual(capture.result.envelope.record_count, 1)
        row = json.loads(capture.result.records[0].data_json)
        self.assertEqual(
            (row["id"], row["title"], row["score"], row["commentCount"]),
            ("abc123", "First post", 42, 12),
        )

    def test_cli_json_is_agent_friendly_and_uses_private_cache(self):
        request = SourceRequest(
            source="reddit", operation="search", locator="fixture",
            parameters_json='{"maxComments":100,"pageSize":1}',
            max_records=1, max_pages=1,
        )
        capture = capture_reddit_pages(
            request,
            (RedditPage(
                url="https://old.reddit.com/search?q=fixture",
                html=(
                    '<div class="thing" data-fullname="t3_abc123" '
                    'data-subreddit="python" data-score="1">'
                    '<a class="title" href="https://example.test">Fixture</a>'
                    '<a class="comments" href="/r/python/comments/abc123/post/">0 comments</a>'
                    '</div>'
                ),
            ),),
            captured_at=NOW,
        )
        observed = {}

        def acquire(source_request, **kwargs):
            observed["request"] = source_request
            observed["cache"] = kwargs["cache_fd"]
            return capture

        stdout, stderr = StringIO(), StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(
                    ["search", "fixture", "1", "--json"],
                    acquire=acquire,
                    cache_root=Path(directory) / "cache",
                )
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertEqual(json.loads(stdout.getvalue())[0]["title"], "Fixture")
        self.assertIsNotNone(observed["cache"])
        self.assertEqual(observed["request"].max_records, 1)

    def test_cli_rejects_an_incomplete_capture_instead_of_printing_empty_success(self):
        incomplete = SimpleNamespace(result=SourceResult(
            envelope=CaptureEnvelope(
                schema_version="1", source="reddit", operation="about",
                requested_locator="python", final_locator="https://www.reddit.com/r/python/",
                captured_at=NOW, collection_mode="rendered", complete=False,
                record_count=0, continuation=None,
                gaps=(CaptureGap(
                    code="empty-results", detail="Reddit returned no observable records",
                    locator="https://www.reddit.com/r/python/",
                ),),
            ),
            records=(), pages=(),
        ))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit) as caught:
                main(
                    ["about", "python", "--json", "--fresh"],
                    acquire=lambda *_args, **_kwargs: incomplete,
                    cache_root=Path(directory) / "cache",
                )
        self.assertIn("empty-results", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
