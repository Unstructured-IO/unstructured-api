from pathlib import Path
from typing import List

import json
import io
import pytest
import requests
import ast
import pandas as pd
from fastapi.testclient import TestClient
from unstructured_api_tools.pipelines.api_conventions import get_pipeline_path

from prepline_general.api.app import app
from unstructured.partition.auto import partition
import tempfile

MAIN_API_ROUTE = get_pipeline_path("general")


def multifile_response_to_dfs(resp: requests.Response) -> List[pd.DataFrame]:
    s = resp.text.split(',"')
    s[0] = s[0][1:]
    s[-1] = s[-1][:-1]
    s[1:] = [f'"{x}' for x in s[1:]]
    return [pd.read_csv(io.StringIO(ast.literal_eval(i))) for i in s]


def test_general_api_health_check():
    client = TestClient(app)
    response = client.get("/healthcheck")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "example_filename, content_type",
    [
        # Note(yuming): Sort filetypes alphabetically according to
        # https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/auto.py#L14
        ("stanley-cups.csv", "application/csv"),
        pytest.param(
            "fake.doc",
            "application/msword",
            marks=pytest.mark.xfail(reason="Encoding not supported yet"),
        ),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("family-day.eml", None),
        ("alert.eml", None),
        ("announcement.eml", None),
        ("fake-email-attachment.eml", None),
        ("fake-email-image-embedded.eml", None),
        ("fake-email.eml", None),
        ("winter-sports.epub", "application/epub"),
        ("fake-html.html", "text/html"),
        ("layout-parser-paper-fast.jpg", "image/jpeg"),
        ("spring-weather.html.json", None),
        ("README.md", "text/markdown"),
        pytest.param("fake-email.msg", None, marks=pytest.mark.xfail(reason="See CORE-1148")),
        ("fake.odt", "application/vnd.oasis.opendocument.text"),
        ("layout-parser-paper.pdf", "application/pdf"),
        ("fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        pytest.param(
            "README.rst", "text/x-rst", marks=pytest.mark.xfail(reason="not supported yet")
        ),
        ("fake-doc.rtf", "application/rtf"),
        ("fake-text.txt", "text/plain"),
        pytest.param(
            "stanley-cups.tsv", "text/tsv", marks=pytest.mark.xfail(reason="not supported yet")
        ),
        pytest.param(
            "fake-excel.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            marks=pytest.mark.xfail(reason="not supported yet"),
        ),
        pytest.param(
            "fake-xml.xml", "application/xml", marks=pytest.mark.xfail(reason="not supported yet")
        ),
    ],
)
def test_general_api(example_filename, content_type):
    client = TestClient(app)
    test_file = Path("sample-docs") / example_filename
    response = client.post(
        MAIN_API_ROUTE, files=[("files", (str(test_file), open(test_file, "rb"), content_type))]
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
            ("files", (str(test_file), open(test_file, "rb"), content_type)),
            ("files", (str(test_file), open(test_file, "rb"), content_type)),
        ],
    )
    assert response.status_code == 200
    assert all(x["metadata"]["filename"] == example_filename for i in response.json() for x in i)

    assert len(response.json()) > 0

    csv_response = client.post(
        MAIN_API_ROUTE,
        files=[
            ("files", (str(test_file), open(test_file, "rb"), content_type)),
            ("files", (str(test_file), open(test_file, "rb"), content_type)),
        ],
        data={"output_format": "text/csv"},
    )
    assert csv_response.status_code == 200
    dfs = multifile_response_to_dfs(csv_response)
    assert len(response.json()) == len(dfs)


def test_coordinates_param():
    """
    Verify that responses do not include coordinates unless requested
    """
    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper-fast.jpg"
    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb")))],
    )

    assert response.status_code == 200
    response_without_coords = response.json()

    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb")))],
        data={"coordinates": "true"},
    )

    assert response.status_code == 200
    response_with_coords = response.json()

    # Each element should be the same except for the coordinates field
    for i in range(len(response_with_coords)):
        assert "coordinates" in response_with_coords[i]
        del response_with_coords[i]["coordinates"]
        assert response_with_coords[i] == response_without_coords[i]


def test_ocr_languages_param():
    """
    ...
    """
    client = TestClient(app)
    test_file = Path("sample-docs") / "english-and-korean.png"
    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb")))],
        data={"strategy": "ocr_only", "ocr_languages": ["eng", "kor"]},
    )

    assert response.status_code == 200
    elements = response.json()
    assert elements[3]["text"].startswith("안녕하세요, 저 희 는 YGEAS 그룹")


def test_strategy_param_400():
    """Verify that we get a 400 if we pass in a bad strategy"""
    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"
    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb"), "text/plain"))],
        data={"strategy": "not_a_strategy"},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "example_filename",
    [
        "fake-xml.xml",
    ],
)
def test_general_api_returns_400_unsupported_file(example_filename):
    client = TestClient(app)
    test_file = Path("sample-docs") / example_filename
    filetype = "application/xml"
    response = client.post(
        MAIN_API_ROUTE, files=[("files", (str(test_file), open(test_file, "rb"), filetype))]
    )
    assert response.json() == {
        "detail": f"Unable to process {str(test_file)}: " f"File type {filetype} is not supported."
    }
    assert response.status_code == 400


def test_general_api_returns_500_bad_pdf():
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf")
    tmp.write(b"This is not a valid PDF")
    client = TestClient(app)
    response = client.post(
        MAIN_API_ROUTE, files=[("files", (str(tmp.name), open(tmp.name, "rb"), "application/pdf"))]
    )
    assert response.json() == {"detail": f"{tmp.name} does not appear to be a valid PDF"}
    assert response.status_code == 400
    tmp.close()


def test_parallel_mode_correct_result(monkeypatch):
    """
    Validate that parallel processing mode merges the results
    to look the same as normal mode
    """
    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"

    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb"), "application/pdf"))],
    )

    assert response.status_code == 200
    result_serial = response.json()

    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_ENABLED", "true")
    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_URL", "unused")
    # Replace our callout with regular old partition
    monkeypatch.setattr(
        "prepline_general.api.general.partition_via_api",
        lambda file, api_url, **kwargs: partition(file=file, **kwargs),
    )

    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb"), "application/pdf"))],
    )

    print(response.text)
    assert response.status_code == 200
    result_parallel = response.json()

    for pair in zip(result_serial, result_parallel):
        print(json.dumps(pair, indent=2))
        assert pair[0] == pair[1]


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_parallel_mode_returns_errors(monkeypatch):
    """
    If we get an error sending a page to the api, bubble it up
    """
    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_ENABLED", "true")
    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_URL", "unused")
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=500),
    )

    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"

    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb"), "application/pdf"))],
        data={"pdf_processing_mode": "parallel"},
    )

    assert response.status_code == 500

    # TODO (austin) - Right now any non 200 is going to turn into a 500
    # because of how partition_via_api_works
    # At the very least we can return a message with a bit more info
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(status_code=400),
    )

    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"

    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(test_file), open(test_file, "rb"), "application/pdf"))],
        data={"pdf_processing_mode": "parallel"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Receive unexpected status code 400 from the API."}
