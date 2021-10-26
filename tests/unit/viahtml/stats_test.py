import json

import importlib_resources
import pytest
from h_matchers import Any
from requests import RequestException

from viahtml.stats import UWSGINewRelicStatsGenerator

STATS_ENDPOINT = "http://example.com"


class TestUWSGINewRelicStatsGenerator:
    def test_it_calls_the_end_point_and_returns_stats(self, stats, requests):
        results = stats()

        assert results == Any.generator.containing([("Custom/Alive/Metrics", 1)])
        requests.get.assert_called_once_with(url=STATS_ENDPOINT, timeout=1)

    def test_it_returns_basic_stats_when_the_request_fails(self, stats, requests):
        requests.get.side_effect = RequestException

        results = stats()

        assert (
            results
            == Any.generator.containing(
                [("Custom/Alive/Metrics", 1), ("Custom/Alive/App", 0)]
            ).only()
        )

    def test_return_values_golden_master(self, stats):
        # A golden master style test to attempt to check that the system hasn't
        # gone catastrophically wrong without writing an un-due amount of test
        # code for this.
        # https://en.wikipedia.org/wiki/Characterization_test

        # This compares a fixed input with a known good output. It's generated
        # exactly as you'd expect by running the test backwards. However the
        # original source has been modified for better tests by varying values
        # to ensure the system is exercised.

        # As this isn't unit-style failures in this test are a canary in a coal
        # mine style results, and help you know that something is wrong, but
        # not what.

        results = list(stats())

        # To maintain these tests when things change print out results, examine
        # them and then set them to expected if they look good
        expected = [
            ("Custom/Alive/Metrics", 1),
            ("Custom/Alive/App", 1),
            ("Custom/System/Load", 16),
            ("Custom/Queue/Listen/Size", 12),
            ("Custom/Queue/Listen/Errors", 13),
            ("Custom/Queue/Signal/Size", 14),
            (
                "Custom/Queue/Socket/Size",
                {"total": 17, "count": 1, "min": 17, "max": 17, "sum_of_squares": 289},
            ),
            (
                "Custom/Queue/Socket/Max",
                {
                    "total": 100,
                    "count": 1,
                    "min": 100,
                    "max": 100,
                    "sum_of_squares": 10000,
                },
            ),
            ("Custom/Worker/Count/Cheap", 6),
            ("Custom/Worker/Count/Idle", 1),
            ("Custom/Worker/Count/Accepting", 5),
            ("Custom/Worker/Count/Max", 7),
            (
                "Custom/Worker/Request/Total",
                {"total": 14, "count": 5, "min": 0, "max": 12, "sum_of_squares": 148},
            ),
            (
                "Custom/Worker/Request/Failed",
                {"total": 7, "count": 5, "min": 0, "max": 5, "sum_of_squares": 29},
            ),
            (
                "Custom/Worker/Count/Killed",
                {"total": 7, "count": 5, "min": 0, "max": 4, "sum_of_squares": 21},
            ),
            (
                "Custom/Worker/Memory/Resident[kiloBytes]",
                {
                    "total": 45871.57,
                    "count": 5,
                    "min": 3.19,
                    "max": 45858.81,
                    "sum_of_squares": 2103030495,
                },
            ),
            (
                "Custom/Worker/AverageResponseTime[ms]",
                {
                    "total": 177.04,
                    "count": 2,
                    "min": 0.34,
                    "max": 176.7,
                    "sum_of_squares": 31223,
                },
            ),
            (
                "Custom/Worker/UpTime[ms]",
                {
                    "total": 354.56,
                    "count": 1,
                    "min": 354.56,
                    "max": 354.56,
                    "sum_of_squares": 125712,
                },
            ),
            (
                "Custom/Worker/Memory/Virtual[kiloBytes]",
                {
                    "total": 766259.2,
                    "count": 1,
                    "min": 766259.2,
                    "max": 766259.2,
                    "sum_of_squares": 587153161584,
                },
            ),
        ]

        for metric_name, value in expected:
            assert (metric_name, value) in results

    @pytest.fixture
    def stats(self):
        return UWSGINewRelicStatsGenerator(stats_endpoint=STATS_ENDPOINT)

    @pytest.fixture
    def json_response(self):
        return json.loads(
            (
                importlib_resources.files("tests.unit.viahtml") / "stats_test.json"
            ).read_bytes()
        )

    @pytest.fixture(autouse=True)
    def requests(self, patch, json_response):
        requests = patch("viahtml.stats.requests")
        requests.get.return_value.json.return_value = json_response

        return requests
