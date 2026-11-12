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

    def test_we_do_not_have_a_coop_header(self, proxied_content):
        # The upstream site sends this header, see `upstream_website()`.
        policy = proxied_content.headers.get("Cross-Origin-Opener-Policy", "*MISSING*")

        assert policy == "*MISSING*"

    def test_we_do_not_have_a_coep_header(self, proxied_content):
        # The upstream site sends this header, see `upstream_website()`.
        policy = proxied_content.headers.get(
            "Cross-Origin-Embedder-Policy", "*MISSING*"
        )

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
        "proxy_frames,expected",
        (
            ("0", True),
            ("1", False),
            (None, False),
        ),
    )
    def test_we_disable_client_side_iframe_proxying_when_proxy_frames_is_off(
        self, app, proxy_frames, expected
    ):
        url = "/proxy/http://localhost:8197/"
        if proxy_frames is not None:
            url += f"?via.proxy_frames={proxy_frames}"

        proxied_content = app.get(url)

        assert (
            "window._WBWombat.prototype.rewriteUrl = function" in proxied_content
        ) == expected

    def test_the_override_resolves_relative_frame_urls(self, app):
        # Left as-is, a relative frame URL would resolve against Via's own
        # address instead of the original site's.
        proxied_content = app.get("/proxy/http://localhost:8197/?via.proxy_frames=0")

        assert "new URL(url, this.wb_info.url).href" in proxied_content

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
