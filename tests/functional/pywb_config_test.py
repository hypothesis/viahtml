import pytest
from pytest import param


class TestPwybConfig:
    # Check non-via pywb setup

    @pytest.mark.parametrize(
        "path",
        (
            param("/", id="index"),
            param("/proxy/", id="collection"),
            param("/proxy/?search=&date-range-from=&date-range-to=", id="search"),
        ),
    )
    def test_irrelevant_pywb_pages_are_disabled(self, app, path):
        result = app.get(path)

        assert result.content_type == "text/html"
        assert b"Page not found" in result.body
