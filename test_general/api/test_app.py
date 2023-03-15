from pathlib import Path
import time

import pytest

from fastapi.testclient import TestClient

from unstructured_api_tools.pipelines.api_conventions import get_pipeline_path

from prepline_general.api.app import app

MAIN_API_ROUTE = get_pipeline_path("general")


def test_general_api_health_check():
    # NOTE(robinson) - Reset the rate limit to avoid 429s in tests
    app.state.limiter.reset()
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
    # NOTE(crag) - Reset below doesn't seem to be working, not sure why. But rate
    # limiting will be removed soon anyway
    time.sleep(1)
    # NOTE(robinson) - Reset the rate limit to avoid 429s in tests
    app.state.limiter.reset()
    client = TestClient(app)
    test_file = Path("sample-docs") / example_filename
    response = client.post(
        MAIN_API_ROUTE, files=[("files", (str(test_file), open(test_file, "rb"), "text/plain"))]
    )
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20
    time.sleep(1)
