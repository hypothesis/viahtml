import pytest


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
            '<link rel="canonical" href="http://localhost:8197/"/>' in proxied_content
        )

    def test_ignore_prefixes_are_added_to_the_wombat_config(self, proxied_content):
        prefixes = (
            'wbinfo.ignore_prefixes = ["http://localhost:5000/", "http://loca'  # ...
        )

        assert prefixes in proxied_content

    def test_we_do_not_have_a_csp_header(self, proxied_content):
        policy = proxied_content.headers.get("Content-Security-Policy", "*MISSING*")

        assert policy == "*MISSING*"

    def test_we_dont_rewrite_links_by_default(self, proxied_content):
        assert '<a href="http://example.com">link</a>' in proxied_content

    def test_we_proxy_iframe_by_default(self, proxied_content):
        assert '<iframe id="proxy-iframe" src="http://localhost' in proxied_content

    def test_we_do_not_proxy_iframe_when_data_viahtml_no_proxy_is_set(
        self, proxied_content
    ):
        assert (
            '<iframe id="no-proxy-iframe" src="http://example.com" data-viahtml-no-proxy></iframe>'
            in proxied_content
        )

    @pytest.mark.parametrize(
        "link_mode,expected",
        (
            ("new-tab", "new-tab"),
            (None, "same-tab"),
        ),
    )
    def test_we_set_external_link_mode(self, app, link_mode, expected):
        url = "/proxy/http://localhost:8197/"
        if link_mode is not None:
            url += f"?via.external_link_mode={link_mode}"

        proxied_content = app.get(url)

        assert f'setupExternalLinkHandler("{expected}");' in proxied_content
