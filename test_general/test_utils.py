from typing import Any

import pytest

from prepline_general.api.utils import SmartValueParser


@pytest.mark.parametrize(
    "desired_type, value_to_parse, expected_result",
    [
        (bool, ["true"], True),
        (int, ["1500"], 1500),
        (float, ["1500"], 1500.0),
        (list[int], [1000], [1000]),
        (bool, True, True),
        (int, 1500, 1500),
        (float, 1500, 1500.0),
        (str, "1500", "1500"),
        (list[str], [["one", "two", "three"]], ["one", "two", "three"]),
        (list[int], [[1000]], [1000]),
    ],
)
def test_smart_value_parser(desired_type: type, value_to_parse: Any, expected_result: Any):
    parsed_value = SmartValueParser[desired_type]().value_or_first_element(value_to_parse)
    assert expected_result == parsed_value
