from h_matchers import Any

from viahtml.views.routing import RoutingView


class TestRoutingView:
    def test_it_skips_non_routing_urls(self, start_response):
        view = RoutingView(routing_host="*any*")

        result = view("/anything", {}, start_response)

        assert result is None
        start_response.assert_not_called()

    def test_it_triggers_for_routing_urls(self, start_response):
        host = "http://example.com"

        view = RoutingView(routing_host=host)
        result = view("/", {}, start_response)

        assert result == []
        start_response.assert_called_once_with(
            "307 Temporary Redirect",
            [
                ("Location", f"{host}/"),
                (
                    "Cache-Control",
                    Any.string.matching(
                        r"public, max-age=\d+, stale-while-revalidate=\d+"
                    ),
                ),
            ],
        )
