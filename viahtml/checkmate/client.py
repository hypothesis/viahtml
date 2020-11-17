"""A client for the Checkmate URL testing service."""

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from viahtml.checkmate.exceptions import CheckmateException
from viahtml.checkmate.response import BlockResponse


class CheckmateClient:
    def __init__(self, host):
        """Create a new client for contacting the Checkmate service.

        :param host: The host including scheme, for the Checkmate service
        """
        self._host = host.rstrip("/")

    def check_url(self, url):
        """Checks a URL for reasons to block.

        :param url: URL to check
        :raises CheckmateException: With any issue with the Checkmate service
        :return: None if the URL is fine or a `CheckmateResponse` if there are
           reasons to block the URL.
        """
        try:
            response = requests.get(
                f"{self._host}/api/check", params={"url": url}, timeout=1
            )
        except (ConnectionError, Timeout) as err:
            raise CheckmateException("Cannot connect to service") from err

        try:
            response.raise_for_status()
        except HTTPError as err:
            raise CheckmateException("Unexpected response from service") from err

        if response.status_code == 204:
            return None

        try:
            return BlockResponse(response.json())

        except ValueError as err:
            raise CheckmateException("Unprocessable JSON response") from err
