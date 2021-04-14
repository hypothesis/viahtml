import json

import httpretty
import pytest


@pytest.mark.usefixtures("httpretty")
class TestStatusView:
    def test_it(self, app):
        httpretty.register_uri(
            httpretty.GET,
            "http://checkmate.example.com/api/check",
            status=500,  # Checkmate crashes.
        )

        response = app.get(
            "/_status",
            params="include-checkmate",
            status=500,  # The status endpoint reports failure.
        )

        assert json.loads(response.body) == {"status": "down", "down": ["checkmate"]}
