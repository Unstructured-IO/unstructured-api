import os
import time
from pathlib import Path

import pytest
import requests
import pandas as pd
import io
import ast

API_URL = "http://localhost:8000/general/v0/general"
# NOTE(rniko): Skip inference tests if we're running on an emulated architecture
skip_inference_tests = os.getenv("SKIP_INFERENCE_TESTS", "").lower() in {"true", "yes", "y", "1"}


def send_document(
    filename,
    content_type,
    strategy="fast",
    output_format="application/json",
    pdf_infer_table_structure="false",
):
    # Note: `content_type` is not passed into request since fast API will overwrite it.
    files = {"files": (str(filename), open(filename, "rb"))}
    return requests.post(
        API_URL,
        files=files,
        data={
            "strategy": strategy,
            "output_format": output_format,
            "pdf_infer_table_structure": pdf_infer_table_structure,
        },
    )


@pytest.mark.parametrize(
    "example_filename, content_type",
    [
        # Note(yuming): Please sort filetypes alphabetically according to
        # https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/auto.py#L14
        ("stanley-cups.csv", "application/csv"),
        ("fake.doc", "application/msword"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("alert.eml", "message/rfc822"),
        ("announcement.eml", "message/rfc822"),
        ("fake-email-attachment.eml", "message/rfc822"),
        ("fake-email-image-embedded.eml", "message/rfc822"),
        ("fake-email.eml", "message/rfc822"),
        ("family-day.eml", "message/rfc822"),
        ("winter-sports.epub", "application/epub"),
        ("fake-html.html", "text/html"),
        pytest.param(
            "layout-parser-paper-fast.jpg",
            "image/jpeg",
            marks=pytest.mark.skipif(skip_inference_tests, reason="emulated architecture"),
        ),
        ("spring-weather.html.json", "application/json"),
        ("README.md", "text/markdown"),
        ("fake-email.msg", "application/x-ole-storage"),
        ("fake.odt", "application/vnd.oasis.opendocument.text"),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Skip these with SKIP_INFERENCE_TESTS=true make docker-test
        pytest.param(
            "layout-parser-paper.pdf",
            "application/pdf",
            marks=pytest.mark.skipif(skip_inference_tests, reason="emulated architecture"),
        ),
        ("fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        ("README.rst", "text/prs.fallenstein.rst"),
        ("fake-doc.rtf", "application/rtf"),
        ("fake-text.txt", "text/plain"),
        ("stanley-cups.tsv", "text/tab-separated-values"),
        (
            "stanley-cups.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        ("fake-xml.xml", "text/xml"),
    ],
)
def test_happy_path(example_filename, content_type):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    test_file = Path("sample-docs") / example_filename
    json_response = send_document(test_file, content_type)

    assert json_response.status_code == 200
    assert len(json_response.json()) > 0
    assert len("".join(elem["text"] for elem in json_response.json())) > 20

    csv_response = send_document(test_file, content_type, output_format="text/csv")
    assert csv_response.status_code == 200
    assert len(csv_response.text) > 0
    df = pd.read_csv(io.StringIO(ast.literal_eval(csv_response.text)))
    assert len(df) == len(json_response.json())


@pytest.mark.skipif(skip_inference_tests, reason="emulated architecture")
def test_strategy_performance():
    """
    For the files in sample-docs, verify that the fast strategy
    is significantly faster than the hi_res strategy
    """
    performance_ratio = 4
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"

    start_time = time.time()
    response = send_document(test_file, content_type="application/pdf", strategy="hi_res")
    hi_res_time = time.time() - start_time
    assert response.status_code == 200

    start_time = time.time()
    response = send_document(test_file, content_type="application/pdf", strategy="fast")
    fast_time = time.time() - start_time
    assert response.status_code == 200

    assert hi_res_time > performance_ratio * fast_time


@pytest.mark.skipif(skip_inference_tests, reason="emulated architecture")
@pytest.mark.parametrize(
    "strategy, pdf_infer_table_structure, expected_table_num",
    [
        ("fast", "True", 0),
        ("fast", "False", 0),
        ("hi_res", "True", 2),
        ("hi_res", "False", 0),
    ],
)
def test_table_support(strategy, pdf_infer_table_structure, expected_table_num):
    """
    Test that table extraction works on hi_res strategy
    """
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"
    response = send_document(
        test_file,
        "application/pdf",
        strategy=strategy,
        pdf_infer_table_structure=pdf_infer_table_structure,
    )

    assert response.status_code == 200
    extracted_tables = [
        el["metadata"]["text_as_html"]
        for el in response.json()
        if "text_as_html" in el["metadata"].keys()
    ]
    assert len(extracted_tables) == expected_table_num
    if expected_table_num > 0:
        # Test a text form a table is extracted
        assert "Layouts of scanned modern magazines and scientific reports" in extracted_tables[0]
