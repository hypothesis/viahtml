import pytest

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
    def test_it_responds_to_the_status_url(self, path, responds, context):
        context.path = path
        StatusView()(context)

        if responds:
            context.make_json_response.assert_called_once()
        else:
            context.make_json_response.assert_not_called()

    def test_it_returns_the_expected_response(self, context):
        context.path = "/_status"

        response = StatusView()(context)

        context.make_json_response.assert_called_once_with(
            {"status": "okay"},
            headers={"Cache-Control": "max-age=0, must-revalidate, no-cache, no-store"},
        )
        assert response == context.make_json_response.return_value
