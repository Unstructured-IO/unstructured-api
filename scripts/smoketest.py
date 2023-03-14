from pathlib import Path
import requests
import time

import pytest

api_url = "http://localhost:8000/general/v0.0.4/general"

def send_document(filename):
    files = {"files": (str(filename), open(filename, "rb"), "text/plain")}
    return requests.post(api_url, files=files)

@pytest.mark.parametrize(
    "example_filename",
    [
        "alert.eml",
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Need to handle this better
        "layout-parser-paper.pdf",
        "layout-parser-paper-fast.jpg",
        pytest.param("fake.doc", marks=pytest.mark.xfail(reason="needs investigation")),
        pytest.param("fake-power-point.ppt", marks=pytest.mark.xfail(reason="needs investigation")),
        "family-day.eml",
        "fake.docx",
        pytest.param("fake-text.txt", marks=pytest.mark.xfail(reason="needs investigation")),
        "fake-html.html",
        pytest.param("fake-excel.xlsx", marks=pytest.mark.xfail(reason="needs investigation")),
        "fake-email.eml",
        "fake-email-image-embedded.eml",
        "fake-email-attachment.eml",
        "announcement.eml",
    ]
)

def test_happy_path(example_filename):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    time.sleep(1)  # Avoid a 429

    test_file = Path("sample-docs") / example_filename
    response = send_document(test_file)

    print(response.text)

    assert(response.status_code == 200)
    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20

    time.sleep(1)
