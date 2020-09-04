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
        "case",
        (
            param(lambda v: v, id="mixed case"),
            param(lambda v: v.lower(), id="lower case"),
            param(lambda v: v.upper(), id="upper case"),
        ),
    )
    @pytest.mark.parametrize("header_name", Headers.BLOCKED_OUTBOUND)
    def test_modify_outbound_removes_blocked_items(self, headers, header_name, case):
        items = (
            ("Other-Header", "ok"),
            (case(header_name), "blocked"),
        )

        items = headers.modify_outbound(items)

        assert items == [("Other-Header", "ok")]

    @pytest.fixture
    def headers(self):
        return Headers()
