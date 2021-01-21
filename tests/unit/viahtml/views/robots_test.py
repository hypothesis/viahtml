import pytest
from h_matchers import Any

from viahtml.views.robots import RobotsView


class TestRobotsView:
    @pytest.mark.parametrize(
        "path,responds",
        (
            ("/robots.txt", True),
            ("/http://example.com", False),
        ),
    )
    def test_it_responds_to_the_robots_txt_url(self, path, responds, start_response):
        response = RobotsView()(path, {}, start_response)

        assert bool(response) == responds

    def test_it_returns_the_expected_response(self, start_response):
        response = RobotsView()("/robots.txt", {}, start_response)

        start_response.assert_called_once_with(
            "200 OK",
            Any.list.containing(
                [
                    ("Cache-Control", "public, max-age=1800"),
                    ("Content-Type", "text/plain"),
                ]
            ).only(),
        )

        assert response == b"User-agent: * \nDisallow: /"
