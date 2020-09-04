import pytest

from viahtml.hooks._headers import Headers


class TestHeaders:
    @pytest.mark.parametrize("header_name", ("Content-Type", "Content-Length"))
    def test_outbound_headers_contain_expected_values(
        self, proxied_content, header_name
    ):
        assert header_name in proxied_content.headers

    @pytest.mark.parametrize("header_name", Headers.BLOCKED_OUTBOUND)
    def test_outbound_headers_do_not_contain_banned_values(
        self, proxied_content, header_name
    ):
        assert header_name not in proxied_content.headers
