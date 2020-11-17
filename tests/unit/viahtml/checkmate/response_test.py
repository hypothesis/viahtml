import pytest
from _pytest.mark import param
from jsonschema import Draft7Validator

from viahtml.checkmate.exceptions import CheckmateException
from viahtml.checkmate.response import BlockResponse


class TestBlockResponse:
    def test_schema_is_valid(self):
        Draft7Validator.check_schema(BlockResponse.VALIDATOR.schema)

    def test_it_parses_a_happy_response(self, payload):
        response = BlockResponse(payload)

        assert response.reason_codes == ["reason_1", "reason_2"]

    @pytest.mark.parametrize(
        "payload",
        (
            param({}, id="blank"),
            param({"data": []}, id="too few data"),
            param({"data": [{}]}, id="id missing"),
            param(
                {"data": [{"id": 1}]},
                id="id not a string",
            ),
        ),
    )
    def test_degenerate_cases(self, payload):
        with pytest.raises(CheckmateException):
            BlockResponse(payload)

    def test_it_stringifies(self, payload):
        response = BlockResponse(payload)

        assert repr(response) == f"BlockResponse({payload})"

    @pytest.fixture
    def payload(self):
        return {
            "data": [{"id": "reason_1", "noise": "random_noise"}, {"id": "reason_2"}],
            "meta": {"maxSeverity": "very_bad", "noise": "random_noise"},
            "noise": "random_noise",
        }
