import httpretty as httpretty_
import pytest


def environment_variables():
    return {
        "VIA_ALLOWED_REFERRERS": ",".join(
            [
                "localhost:8001",
            ]
        ),
        "VIA_H_EMBED_URL": "http://localhost:3001/hypothesis",
        "VIA_IGNORE_PREFIXES": ",".join(
            [
                "http://localhost:5000/",
                "http://localhost:3001/",
                "https://localhost:5000/",
                "https://localhost:3001/",
            ]
        ),
        "VIA_DISABLE_AUTHENTICATION": "0",
        "VIA_DEBUG": "1",
        "VIA_ROUTING_HOST": "http://example.com/via3",
        "CHECKMATE_URL": "http://checkmate.example.com",
        "CHECKMATE_API_KEY": "dev_api_key",
        "CHECKMATE_IGNORE_REASONS": "",
    }


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
