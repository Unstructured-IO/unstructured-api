from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from prepline_general.api.app import app

MAIN_API_ROUTE = "general/v0/general"


@pytest.mark.parametrize(
    "parameters",
    [
        pytest.param({"coordinates": ["true"]}, id="coordinates_true"),
        pytest.param({"coordinates": ["false"]}, id="coordinates_false"),
        pytest.param({"encoding": ["utf-8"]}, id="encoding"),
        pytest.param({"hi_res_model_name": ["yolox"]}, id="hi_res_model_name"),
        pytest.param({"include_page_breaks": ["true"]}, id="include_page_breaks"),
        pytest.param({"ocr_languages": ["eng", "kor"]}, id="ocr_languages"),
        pytest.param({"languages": ["eng", "kor"]}, id="languages"),
        pytest.param({"languages": ["eng", "kor"]}, id="languages_inner"),
        pytest.param({"pdf_infer_table_structure": ["false"]}, id="pdf_infer_table_structure"),
        pytest.param({"skip_infer_table_types": ["false"]}, id="skip_infer_table_types"),
        pytest.param({"strategy": ["hi_res"]}, id="strategy"),
        pytest.param({"xml_keep_tags": ["false"]}, id="xml_keep_tags"),
        pytest.param({"extract_image_block_types": ["image"]}, id="extract_image_block_types"),
        pytest.param(
            {"extract_image_block_types": ['["image", "table"]']},
            id="extract_image_block_types_json",
        ),
        pytest.param({"chunking_strategy": ["by_title"]}, id="chunking_strategy"),
        pytest.param({"multipage_sections": ["false"]}, id="multipage_sections"),
        pytest.param({"combine_under_n_chars": ["500"]}, id="combine_under_n_chars"),
        pytest.param({"new_after_n_chars": ["1500"]}, id="new_after_n_chars"),
        pytest.param({"max_characters": ["1500"]}, id="max_characters"),
    ],
)
def test_form_params_passed_as_first_element_of_array_are_properly_handled(
    parameters: dict[str, Any],
):
    """
    Verify that responses do not include coordinates unless requested
    Verify that certain other metadata fields are dropped
    """
    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper-fast.jpg"
    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb")))],
        data=parameters,
    )

    assert response.status_code == 200
    assert response.json()
