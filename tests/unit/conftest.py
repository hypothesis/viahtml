import os

import pytest


@pytest.fixture(autouse=True)
def with_environ():
    # WSGI uses repeated elements to express this, which means we can't use
    # the standard configparser.ConfigParser to read them. So they are
    # duplicated here:
    os.environ.update(
        {
            "VIA_H_EMBED_URL": "http://localhost:3001/hypothesis",
            "VIA_IGNORE_PREFIXES": (
                # This is one string
                "http://localhost:5000/,http://localhost:3001/,"
                "https://localhost:5000/,https://localhost:3001/"
            ),
            "VIA_DEBUG": "1",
        }
    )
