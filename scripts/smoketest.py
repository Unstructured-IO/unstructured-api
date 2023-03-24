from pathlib import Path
import requests
import time

import pytest

api_url = "http://localhost:8000/general/v0.0.5/general"

def send_document(filename):
    files = {"files": (str(filename), open(filename, "rb"), "text/plain")}
    return requests.post(api_url, files=files)

@pytest.mark.parametrize(
    "example_filename",
    [
        "alert.eml",
        "announcement.eml",
        "fake-email-attachment.eml",
        "fake-email-image-embedded.eml",
        "fake-email.eml",
        "fake-html.html",
        pytest.param("fake-power-point.ppt", marks=pytest.mark.xfail(reason="See CORE-796")),
        "fake-text.txt",
        "fake.doc",
        "fake.docx",
        "family-day.eml",
        pytest.param("fake-excel.xlsx", marks=pytest.mark.xfail(reason="not supported yet")),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Need to handle this better
        "layout-parser-paper.pdf",
        "layout-parser-paper-fast.jpg",
    ]
)

def test_happy_path(example_filename):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    test_file = Path("sample-docs") / example_filename
    response = send_document(test_file)

    print(response.text)

    assert(response.status_code == 200)
    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20
