import pytest
from pytest import param

from viahtml.hooks._headers import Headers


class TestHeaders:
    def test_environ_name(self):
        assert Headers.environ_name("mIxed-Case") == "HTTP_MIXED_CASE"

    @pytest.mark.parametrize("header_name", Headers.BLOCKED_INBOUND)
    def test_modify_inbound_removes_blocked_items(self, headers, header_name):
        http_env = {
            "HTTP_OTHER_HEADER": "ok",
            Headers.environ_name(header_name): "blocked",
        }

        http_env = headers.modify_inbound(http_env)

        assert Headers.environ_name(header_name) not in http_env
        assert "HTTP_OTHER_HEADER" in http_env

    @pytest.mark.parametrize(
        "header_name", Headers.BLOCKED_OUTBOUND - {"X-Archive-Orig-Cache-Control"}
    )
    def test_modify_outbound_removes_blocked_items(
        self, headers, header_name, string_case
    ):
        items = (
            ("Other-Header", "ok"),
            (string_case(header_name), "blocked"),
        )

        items = headers.modify_outbound(items)

        assert items == [("Other-Header", "ok")]

    @pytest.mark.parametrize(
        "value,expected",
        (
            # Things we don't mess with
            ("invalid_header", "invalid_header"),
            ("no-cache, must-revalidate", "no-cache, must-revalidate"),
            ("max-age=604800", "max-age=604800"),
            ("private, max-age=0", "private, max-age=0"),
            ("private, max-age=604800", "private, max-age=604800"),
            # When the cache is public, and below cloudflare caching numbers, we
            # mark it as private only. The order changes a bit here too
            ("public, max-age=0", "max-age=0, private"),
            ("public, max-age=100", "max-age=100, private"),
            # Back to over the Cloudflare minimum
            ("public, max-age=604800", "public, max-age=604800"),
        ),
    )
    def test_cache_control_translation(self, headers, value, expected, string_case):
        items = headers.modify_outbound(
            ((string_case("X-Archive-Orig-Cache-Control"), value),)
        )

        assert items == [("Cache-Control", expected)]

    @pytest.fixture(
        params=(
            param(lambda v: v, id="mixed case"),
            param(lambda v: v.lower(), id="lower case"),
            param(lambda v: v.upper(), id="upper case"),
        )
    )
    def string_case(self, request):
        return request.param

    @pytest.fixture
    def headers(self):
        return Headers()
