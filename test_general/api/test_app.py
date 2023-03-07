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


#@pytest.mark.parametrize(
#    "example_filename",
#    [
#        "layout-parser-paper.pdf",
#        "layout-parser-paper-fast.jpg",
#        pytest.param("fake.doc", marks=pytest.mark.xfail(reason="needs investigation")),
#        pytest.param("fake-power-point.ppt", marks=pytest.mark.xfail(reason="needs investigation")),
#        "family-day.eml",
#        "fake.docx",
#        pytest.param("fake-text.txt", marks=pytest.mark.xfail(reason="needs investigation")),
#        "fake-power-point.pptx",
#        "fake-html.html",
#        pytest.param("fake-excel.xlsx", marks=pytest.mark.xfail(reason="needs investigation")),
#        "fake-email.eml",
#        "fake-email-image-embedded.eml",
#        "fake-email-attachment.eml",
#        "announcement.eml",
#        "alert.eml",
#    ],
#)
#def test_general_api(example_filename):
#    # NOTE(crag) - Reset below doesn't seem to be working, not sure why. But rate
#    # limiting will be removed soon anyway
#    time.sleep(1)
#    # NOTE(robinson) - Reset the rate limit to avoid 429s in tests
#    app.state.limiter.reset()
#    client = TestClient(app)
#    test_file = Path("sample-docs") / example_filename
#    response = client.post(
#        MAIN_API_ROUTE, files=[("files", (str(test_file), open(test_file, "rb"), "text/plain"))]
#    )
#    assert response.status_code == 200
#    assert len(response.json()) > 0
#    assert len("".join(elem["text"] for elem in response.json())) > 20
#    time.sleep(1)
