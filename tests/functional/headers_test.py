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

    def test_cache_control_translation(self, proxied_content):
        # This is set in the content served, we're looking for public to become
        # private as the time is lower than the Cloudflare minimum
        assert proxied_content.headers["Cache-Control"] == "max-age=60, private"
