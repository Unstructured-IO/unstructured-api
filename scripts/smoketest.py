import os
import tempfile
import time
from pathlib import Path

import pytest
import requests
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_csv

API_URL = "http://localhost:8000/general/v0/general"
# NOTE(rniko): Skip inference tests if we're running on an emulated architecture
skip_inference_tests = os.getenv("SKIP_INFERENCE_TESTS", "").lower() in {"true", "yes", "y", "1"}


def send_document(filename, content_type, strategy="fast", output_format="application/json"):
    files = {"files": (str(filename), open(filename, "rb"))}
    return requests.post(API_URL, files=files, data={"strategy": strategy, "output_format": output_format})


# NOTE(kravetsmic): This function was added for removing path from text/csv response because the backend has a different
# temporary path than the temporary path in tests
def remove_path(text: str) -> str:
    try:
        rows = text.split("\r\n")
        filename_index = rows[0].split(",").index("filename")
    except ValueError:
        return text
    for row_index in range(len(rows[1:])):
        row_strings_arr = rows[row_index].split(",")
        row_strings_arr[filename_index] = ""
        rows[row_index] = ",".join(row_strings_arr)
    return "\r\n".join(rows)

@pytest.mark.parametrize(
    "example_filename, content_type, output_format, strategy",
    [
        ("alert.eml", "message/rfc822", "application/json", "fast"),
        ("announcement.eml", "message/rfc822", "application/json", "fast"),
        ("fake-email-attachment.eml", "message/rfc822", "application/json", "fast"),
        ("fake-email-image-embedded.eml", "message/rfc822", "application/json", "fast"),
        ("fake-email.eml", "message/rfc822", "application/json", "fast"),
        ("fake-html.html", "text/html", "application/json", "fast"),
        ("fake-power-point.ppt", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/json", "fast"),
        ("fake-text.txt", "text/plain", "application/json", "fast"),
        ("fake.doc", "application/msword", "application/json", "fast"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/json", "fast"),
        ("family-day.eml", "message/rfc822", "application/json", "fast"),
        pytest.param("fake-excel.xlsx", None, "application/json", "fast", marks=pytest.mark.xfail(reason="not supported yet")),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Skip these with SKIP_INFERENCE_TESTS=true make docker-test
        pytest.param("layout-parser-paper.pdf", "application/pdf", "application/json", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg", "image/jpeg", "application/json", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        ("fake-text.txt", "text/plain", "text/csv", "fast"),
        ("announcement.eml", "text/plain", "text/csv", "fast"),
        ("fake-email-attachment.eml", "text/plain", "text/csv", "fast"),
        ("fake-email-image-embedded.eml", "text/plain", "text/csv", "fast"),
        ("fake-email.eml", "text/plain", "text/csv", "fast"),
        ("fake-html.html", "text/plain", "text/csv", "fast"),
        ("fake-power-point.ppt", "text/plain", "text/csv", "fast"),
        ("fake.doc", "text/plain", "text/csv", "fast"),
        ("fake.docx", "text/plain", "text/csv", "fast"),
        ("family-day.eml", "text/plain", "text/csv", "fast"),
        pytest.param("fake-excel.xlsx", None, "text/csv", "fast", marks=pytest.mark.xfail(reason="not supported yet")),
        pytest.param("layout-parser-paper.pdf", "application/pdf", "text/csv", "hi_res", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg", "image/jpeg", "text/csv", "hi_res", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
    ]
)
def test_happy_path(example_filename, content_type, output_format, strategy):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    test_file = Path("sample-docs") / example_filename
    response = send_document(
        filename=test_file,
        strategy=strategy,
        content_type=content_type,
        output_format=output_format,
    )

    assert(response.status_code == 200)
    assert len(response.json()) > 0
    # NOTE(kravetsmic): looks like a bug on macOS (m1), incorrectly scanned text from images and pdf files
    if output_format == "text/csv" and example_filename not in ["layout-parser-paper.pdf", "layout-parser-paper-fast.jpg"]:
        if isinstance(test_file, str) and test_file.endswith((".docx", ".pptx")):
            with tempfile.TemporaryDirectory() as tmpdir:
                _filename = os.path.join(tmpdir, test_file.split('/')[-1])
                with open(_filename, "wb") as f:
                    with open(test_file, "rb") as test_f:
                        f.write(test_f.read())
            elements = partition(filename=_filename, strategy=strategy)
        else:
            with open(test_file, "rb") as file:
                elements = partition(
                    file=file,
                    file_filename=str(test_file),
                    content_type=content_type,
                    strategy=strategy
                )
        assert remove_path(response.json()) == remove_path(convert_to_csv(elements))
    else:
        assert len("".join(elem["text"] for elem in response.json())) > 20


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
