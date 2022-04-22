import os

# isort: off
# This import has to come before the CheckmateClient import or the functional
# tests break.
# See https://github.com/gevent/gevent/issues/1016
import pywb.apps.frontendapp  # pylint:disable=unused-import

# isort: on

import httpretty as httpretty_
import pytest
import webtest

from tests.conftest import environment_variables
from tests.simple_server import serve_content
from viahtml.app import Application


@pytest.fixture(scope="session")
def app(with_environ):  # pylint:disable=unused-argument
    app = Application()
    app.debug = True

    return webtest.TestApp(app)


@pytest.fixture(scope="session")
def with_environ():
    # WSGI uses repeated elements to express this, which means we can't use
    # the standard configparser.ConfigParser to read them. So they are
    # duplicated here:

    # It's very hard to test with URL signing on, so disable it
    env_vars = environment_variables()
    env_vars["VIA_DISABLE_AUTHENTICATION"] = "1"

    os.environ.update(env_vars)


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
         <a href="http://example.com">link</a>
       </body>
     </html>
     """

    with serve_content(  # pylint: disable=not-context-manager
        minimal_valid_html,
        port=8197,
        extra_headers={"Cache-Control": "public, max-age=60"},
    ):
        yield


@pytest.fixture
def proxied_content(app):
    return app.get(
        "/proxy/http://localhost:8197/?via.client.openSidebar=yup", expect_errors=True
    )


@pytest.fixture
def httpretty():
    """Monkey-patch Python's socket core module to mock all HTTP responses.

    We never want real HTTP requests to be sent by the tests so replace them
    all with mock responses. This handles requests sent using the standard
    urllib2 library and the third-party httplib2 and requests libraries.
    """
    httpretty_.enable(allow_net_connect=False)

    yield

    httpretty_.disable()
    httpretty_.reset()
