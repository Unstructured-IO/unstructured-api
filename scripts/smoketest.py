import os
import time
from pathlib import Path

import pytest
import requests

API_URL = "http://localhost:8000/general/v0/general"
# NOTE(rniko): Skip inference tests if we're running on an emulated architecture
skip_inference_tests = os.getenv("SKIP_INFERENCE_TESTS", "").lower() in {"true", "yes", "y", "1"}


def send_document(filename, content_type, strategy="fast"):
    files = {"files": (str(filename), open(filename, "rb"), content_type)}
    return requests.post(API_URL, files=files, data={"strategy": strategy})


@pytest.mark.parametrize(
    "example_filename, content_type",
    [
        ("alert.eml", None),
        ("announcement.eml", None),
        ("fake-email-attachment.eml", None),
        ("fake-email-image-embedded.eml", None),
        ("fake-email.eml", None),
        ("fake-html.html", None),
        pytest.param("fake-power-point.ppt", None, marks=pytest.mark.xfail(reason="See CORE-796")),
        ("fake-text.txt", "text/plain"),
        ("fake.doc", "application/msword"),
        ("fake.docx", None),
        ("family-day.eml", None),
        pytest.param("fake-excel.xlsx", None, marks=pytest.mark.xfail(reason="not supported yet")),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Need to handle this better
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

    print(response.text)

    assert(response.status_code == 200)
    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20


def test_strategy_performance():
    """
    For the files in sample-docs, verify that the fast strategy
    is significantly faster than the hi_res strategy
    """
    performance_ratio = 4
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"

    start_time = time.time()
    response = send_document(test_file, strategy="hi_res")
    hi_res_time = time.time() - start_time
    assert(response.status_code == 200)

    start_time = time.time()
    response = send_document(test_file, strategy="fast")
    fast_time = time.time() - start_time
    assert(response.status_code == 200)

    assert hi_res_time > performance_ratio * fast_time
