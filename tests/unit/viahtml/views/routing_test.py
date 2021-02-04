from http import HTTPStatus

from h_matchers import Any

from viahtml.views.routing import RoutingView


class TestRoutingView:
    def test_it_triggers_for_the_root(self, context):
        context.path = "/"
        host = "http://example.com"

        view = RoutingView(routing_host=host)
        result = view(context)

        context.make_response.assert_called_once_with(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={
                "Location": f"{host}/",
                "Cache-Control": Any.string.matching(
                    r"public, max-age=\d+, stale-while-revalidate=\d+"
                ),
            },
        )
        assert result == context.make_response.return_value

    def test_it_skips_all_other_paths(self, context):
        context.path = "/anything"
        view = RoutingView(routing_host="*any*")

        result = view(context)

        assert result is None
        context.start_response.assert_not_called()
