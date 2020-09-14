from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def os():
    with patch("viahtml.app.os", autospec=True) as os:
        os.environ = {
            "VIA_H_EMBED_URL": "http://localhost:3001/hypothesis",
            "VIA_IGNORE_PREFIXES": (
                # This is one string
                "http://localhost:5000/,http://localhost:3001/,"
                "https://localhost:5000/,https://localhost:3001/"
            ),
            "VIA_DEBUG": "1",
        }
        yield os
