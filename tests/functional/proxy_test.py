import pytest

from tests.simple_server import serve_content


class TestProxy:
    # Test our the core proxying behavior and our additions to it

    def test_we_can_proxy_a_page(self, proxied_content):
        assert "upstream content" in proxied_content

    def test_client_embed_is_in_the_page(self, proxied_content):
        assert (
            'embed_script.src = "http://localhost:3001/hypothesis"' in proxied_content
        )

    def test_client_params_are_passed_through(self, proxied_content):
        assert '"openSidebar": "yup"' in proxied_content

    def test_client_params_are_stripped_from_the_canonical_url(self, proxied_content):
        assert (
            '<link rel="canonical" href="http://localhost:8080/"/>' in proxied_content
        )

    def test_ignore_prefixes_are_added_to_the_wombat_config(self, proxied_content):
        prefixes = (
            'wbinfo.ignore_prefixes = ["http://localhost:5000/", "http://loca'  # ...
        )

        assert prefixes in proxied_content

    def test_we_do_not_have_a_csp_header(self, proxied_content):
        policy = proxied_content.headers.get("Content-Security-Policy", "*MISSING*")

        assert policy == "*MISSING*"
