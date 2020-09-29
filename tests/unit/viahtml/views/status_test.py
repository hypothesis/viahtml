import json

import pytest
from h_matchers import Any

from viahtml.views.status import StatusView


class TestStatusView:
    @pytest.mark.parametrize(
        "path,responds",
        (
            ("/_status", True),
            ("/_status/", True),
            ("/http://example.com", False),
        ),
    )
    def test_it_responds_to_the_status_url(self, path, responds, start_response):
        response = StatusView()({"PATH_INFO": path}, start_response)

        assert bool(response) == responds

    def test_it_returns_the_expected_response(self, start_response):
        response = StatusView()({"PATH_INFO": "/_status"}, start_response)

        start_response.assert_called_once_with(
            "200 OK",
            Any.list.containing(
                [
                    ("Cache-Control", "no-cache"),
                    ("Content-Type", "application/json; charset=utf-8"),
                ]
            ).only(),
        )

        assert isinstance(response, list)
        body = json.loads(response[0])
        assert body == {"status": "okay"}
