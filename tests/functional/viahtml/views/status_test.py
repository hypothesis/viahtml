import json

import httpretty
import pytest


@pytest.mark.usefixtures("httpretty")
class TestStatusView:
    def test_it(self, app):
        httpretty.register_uri(
            httpretty.GET, "http://checkmate.example.com/api/check", status=204
        )

        response = app.get("/_status")

        assert json.loads(response.body) == {"status": "okay"}

    def test_it_when_calling_checkmate_fails(self, app):
        httpretty.register_uri(
            httpretty.GET, "http://checkmate.example.com/api/check", status=500
        )

        response = app.get("/_status")

        assert json.loads(response.body) == {"status": "checkmate_failure"}
