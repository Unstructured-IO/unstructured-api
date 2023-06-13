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


def send_document(filename, content_type, strategy="fast", output_format="application/json"):
    files = {"files": (str(filename), open(filename, "rb"))}
    return requests.post(API_URL, files=files, data={"strategy": strategy, "output_format": output_format})


@pytest.mark.parametrize(
    "example_filename, content_type",
    [
        ("alert.eml", "message/rfc822"),
        ("announcement.eml", "message/rfc822"),
        ("fake-email-attachment.eml", "message/rfc822"),
        ("fake-email-image-embedded.eml", "message/rfc822"),
        ("fake-email.eml", "message/rfc822"),
        ("fake-html.html", "text/html"),
        ("fake-power-point.ppt", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("fake-text.txt", "text/plain"),
        ("fake.doc", "application/msword"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("family-day.eml", "message/rfc822"),
        ("winter-sports.epub", "application/epub"),
        ("fake-doc.rtf", "application/rtf"),
        ("fake.odt", "application/vnd.oasis.opendocument.text"),
        ("stanley-cups.csv", "application/csv"),
        pytest.param("fake-excel.xlsx", None, marks=pytest.mark.xfail(reason="not supported yet")),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Skip these with SKIP_INFERENCE_TESTS=true make docker-test
        pytest.param("layout-parser-paper.pdf", "application/pdf", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg", "image/jpeg", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        )
    ]
)
def test_happy_path(example_filename, content_type):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    test_file = Path("sample-docs") / example_filename
    response = send_document(test_file, content_type)

    assert(response.status_code == 200)
    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20


@pytest.mark.parametrize(
    "example_filename, content_type",
    [
        ("alert.eml", "message/rfc822"),
        ("announcement.eml", "message/rfc822"),
        ("fake-email-attachment.eml", "message/rfc822"),
        ("fake-email-image-embedded.eml", "message/rfc822"),
        ("fake-email.eml", "message/rfc822"),
        ("fake-html.html", "text/html"),
        ("fake-power-point.ppt", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("fake-text.txt", "text/plain"),
        ("fake.doc", "application/msword"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("family-day.eml", "message/rfc822"),
        ("winter-sports.epub", "application/epub"),
        ("fake-doc.rtf", "application/rtf"),
        ("fake.odt", "application/vnd.oasis.opendocument.text"),
        ("stanley-cups.csv", "application/csv"),
        pytest.param("fake-excel.xlsx", None, marks=pytest.mark.xfail(reason="not supported yet")),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Skip these with SKIP_INFERENCE_TESTS=true make docker-test
        pytest.param("layout-parser-paper.pdf", "application/pdf", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg", "image/jpeg", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        )
    ]
)
def test_csv_output(example_filename, content_type):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    test_file = Path("sample-docs") / example_filename
    response = send_document(test_file, content_type, output_format="text/csv")

    assert(response.status_code == 200)
    df = pd.read_csv(io.StringIO(ast.literal_eval(response.text)))
    assert len(df) > 0



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
    assert(response.status_code == 200)

    start_time = time.time()
    response = send_document(test_file, content_type="application/pdf", strategy="fast")
    fast_time = time.time() - start_time
    assert(response.status_code == 200)

    assert hi_res_time > performance_ratio * fast_time
