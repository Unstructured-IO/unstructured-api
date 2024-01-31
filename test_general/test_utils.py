from typing import Any

import pytest

from prepline_general.api.utils import SmartValueParser


@pytest.mark.parametrize(
    "desired_type, value_to_parse, expected_result",
    [
        (bool, ["true"], True),
        (bool, "true", True),
        (bool, ["false"], False),
        (bool, True, True),
        (bool, "false", False),
        (bool, False, False),
        (int, "1500", 1500),
        (int, ["1500"], 1500),
        (float, ["1500"], 1500.0),
        (list[int], [1000], [1000]),
        (int, 1500, 1500),
        (float, 1500, 1500.0),
        (str, "1500", "1500"),
        (float, "1500", 1500.0),
        (list[str], ["one", "two", "three"], ["one", "two", "three"]),
        (list[int], [1000], [1000]),
        (list[bool], ["true", "False", "True"], [True, False, True]),
    ],
)
def test_smart_value_parser(desired_type: type, value_to_parse: Any, expected_result: Any):
    parsed_value = SmartValueParser[desired_type]().value_or_first_element(value_to_parse)
    assert expected_result == parsed_value
