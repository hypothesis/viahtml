"""A response from the Checkmate service with reasons to block."""

import json

from jsonschema import Draft7Validator
from pkg_resources import resource_string

from viahtml.checkmate.exceptions import CheckmateException


class BlockResponse:
    """A response from the Checkmate service with reasons to block."""

    VALIDATOR = Draft7Validator(
        json.loads(resource_string("viahtml.checkmate", "response_schema.json"))
    )

    def __init__(self, payload):
        """Creates a response object from the given response from Checkmate.

        :raises CheckmateException: If the payload is malformed
        :param payload: Decoded JSON response from the Checkmate service.
        """
        for error in self.VALIDATOR.iter_errors(payload):
            raise CheckmateException(f"Unparseable response: {error}")

        self._payload = payload

    @property
    def reason_codes(self):
        """Get the list of reason codes."""
        return [reason["id"] for reason in self._payload["data"]]

    def __repr__(self):
        return f"BlockResponse({repr(self._payload)})"
