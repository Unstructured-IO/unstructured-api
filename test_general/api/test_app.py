from pathlib import Path

import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient

from unstructured_api_tools.pipelines.api_conventions import get_pipeline_path

from prepline_general.api.app import app

MAIN_API_ROUTE = get_pipeline_path("general")


def test_general_api_health_check():
    client = TestClient(app)
    response = client.get("/healthcheck")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "example_filename",
    [
        "alert.eml",
        "announcement.eml",
        "fake-email-attachment.eml",
        "fake-email-image-embedded.eml",
        "fake-email.eml",
        pytest.param("fake-excel.xlsx", marks=pytest.mark.xfail(reason="not supported yet")),
        "fake-html.html",
        "fake-power-point.ppt",
        "fake-text.txt",
        "fake.doc",
        "fake.docx",
        "family-day.eml",
        "layout-parser-paper-fast.jpg",
        "layout-parser-paper.pdf",
    ],
)
def test_general_api(example_filename):
    client = TestClient(app)
    test_file = Path("sample-docs") / example_filename
    response = client.post(
        MAIN_API_ROUTE, files=[("files", (str(test_file), open(test_file, "rb"), "text/plain"))]
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
    for i in response.json():
        assert i["metadata"]["filename"] == example_filename
    assert len("".join(elem["text"] for elem in response.json())) > 20

    # Just hit the second path (posting multiple files) to bump the coverage
    # We'll come back and make smarter tests
    response = client.post(
        MAIN_API_ROUTE,
        files=[
            ("files", (str(test_file), open(test_file, "rb"), "text/plain")),
            ("files", (str(test_file), open(test_file, "rb"), "text/plain")),
        ],
    )
    assert response.status_code == 200
    assert all(x["metadata"]["filename"] == example_filename for i in response.json() for x in i)

    assert len(response.json()) > 0


@pytest.mark.parametrize(
    "example_filename",
    [
        "fake-xml.xml",
    ],
)
def test_general_api_returns_400(example_filename):
    client = TestClient(app)
    test_file = Path("sample-docs") / example_filename
    filetype = "application/xml"
    response = client.post(
        MAIN_API_ROUTE, files=[("files", (str(test_file), open(test_file, "rb"), filetype))]
    )
    assert response.json() == {"detail": f"{filetype} not currently supported"}
    assert response.status_code == 400
