from unittest.mock import patch, sentinel

import pytest
from h_matchers import Any

from viahtml.hooks import Hooks


class TestHooks:
    def test_template_vars(self, hooks):
        assert hooks.template_vars == {
            "client_params": Any.function(),
            "external_link_mode": Any.function(),
            "ignore_prefixes": hooks.ignore_prefixes,
        }

    def test_client_params_in_template_vars(self, hooks):
        with patch.object(hooks, "get_config") as get_config:
            get_config.return_value = ["via", "client"]
            client_params = hooks.template_vars["client_params"]

            params = client_params(sentinel.http_env)

            assert params == "client"
            get_config.assert_called_once_with(sentinel.http_env)

    @pytest.mark.parametrize(
        "link_mode,expected",
        (
            ("new-tab", "new-tab"),
            ("same-tab", "same-tab"),
            (None, "same-tab"),
            ("random", "random"),
        ),
    )
    def test_external_link_mode_in_template_vars(self, hooks, link_mode, expected):
        http_env = {}
        if link_mode is not None:
            http_env["QUERY_STRING"] = f"via.external_link_mode={link_mode}"

        external_link_mode = hooks.template_vars["external_link_mode"]

        assert external_link_mode(http_env) == expected

    def test_ignore_prefixes(self, hooks):
        assert hooks.ignore_prefixes == sentinel.prefixes

    def test_get_config(self, Configuration, hooks):
        config = hooks.get_config(sentinel.http_env)

        Configuration.extract_from_wsgi_environment.assert_called_once_with(
            sentinel.http_env
        )
        assert config == Configuration.extract_from_wsgi_environment.return_value

    def test_get_upstream_url(self, Configuration):
        config = Hooks({}).get_upstream_url(sentinel.doc_url)

        Configuration.strip_from_url.assert_called_once_with(sentinel.doc_url)
        assert config == Configuration.strip_from_url.return_value

    @pytest.fixture
    def hooks(self):
        return Hooks({"ignore_prefixes": sentinel.prefixes})

    @pytest.fixture
    def Configuration(self):
        with patch("viahtml.hooks.hooks.Configuration", autospec=True) as Configuration:
            yield Configuration
