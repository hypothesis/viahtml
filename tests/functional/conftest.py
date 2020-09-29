import os

import pytest
import webtest

from tests.simple_server import serve_content
from viahtml.app import Application


@pytest.fixture(scope="session")
def app(with_environ):
    app = Application()
    app.debug = True

    return webtest.TestApp(app)


@pytest.fixture(scope="session")
def with_environ():
    # WSGI uses repeated elements to express this, which means we can't use
    # the standard configparser.ConfigParser to read them. So they are
    # duplicated here:
    os.environ.update(
        {
            "VIA_H_EMBED_URL": "http://localhost:3001/hypothesis",
            "VIA_IGNORE_PREFIXES": ",".join(
                [
                    "http://localhost:5000/",
                    "http://localhost:3001/",
                    "https://localhost:5000/",
                    "https://localhost:3001/",
                ]
            ),
            "VIA_DEBUG": "1",
        }
    )


@pytest.fixture(autouse=True, scope="session")
def upstream_website():
    minimal_valid_html = """
     <!DOCTYPE html>
     <html lang="en">
       <head>
         <meta charset="utf-8">
         <title>title</title>
         <link rel="manifest" href="/manifest.json" type="text/javascript">
         <link rel="other" href="/other.json" type="text/javascript">
         <script src="script.js"></script>
       </head>
       <body>
         <!-- upstream content -->
       </body>
     </html>
     """

    with serve_content(
        minimal_valid_html,
        port=8080,
        extra_headers={"Cache-Control": "public, max-age=60"},
    ):
        yield


@pytest.fixture
def proxied_content(app):
    return app.get(
        "/proxy/http://localhost:8080/?via.client.openSidebar=yup", expect_errors=True
    )
