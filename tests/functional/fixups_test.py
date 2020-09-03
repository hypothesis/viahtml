class TestFixupsToPywb:
    # Test random fixups we've made to improve `pywb` behavior

    def test_we_do_not_try_and_rewrite_rel_manifest(self, proxied_content):
        # The '_id' here means a transparent rewrite, and no insertion of
        # wombat stuff
        assert (
            '<link rel="manifest" href="/proxy/id_/http://localhost:8080/manifest.json"'
            in proxied_content
        )

    def test_we_do_rewrite_other_rels(self, proxied_content):
        print(proxied_content)
        assert (
            '<link rel="other" href="/proxy/oe_/http://localhost:8080/other.json"'
            in proxied_content
        )
