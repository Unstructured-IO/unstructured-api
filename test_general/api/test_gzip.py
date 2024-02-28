import tempfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from deepdiff import DeepDiff

from prepline_general.api.app import app

MAIN_API_ROUTE = "general/v0/general"


def gzip_file(in_filepath: str, out_filepath: str):
    import gzip
    import shutil
    with open(in_filepath, 'rb') as f_in:
        with gzip.open(out_filepath, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
            print(f"Copied gzip to {out_filepath}")


def call_api(client: TestClient, filename: str, content_type: str, options: dict) -> httpx.Response:
    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(filename), open(filename, "rb"), content_type))],
        data=options,
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) > 0
    return response


@pytest.mark.parametrize(
    "example_filename, gz_uncompressed_content_type",
    [
        ("fake-html.html", "text/html"),
        ("stanley-cups.csv", "application/csv"),
        ("fake.doc", "application/msword"),
        ("layout-parser-paper-fast.pdf", "application/pdf"),
    ]
)
def test_single_gzipped_file_is_parsed_same_as_original_explicit_gz_type(example_filename: str, gz_uncompressed_content_type: str):
    """
    Verify that API supports unzipping gzip and correctly interprets gz_uncompressed_content_type
    by comparing response to directly parsing the same file.
    """

    original_file = Path("sample-docs") / example_filename
    client = TestClient(app)

    with tempfile.NamedTemporaryFile(suffix=".csv.gz") as temp_file:
        gzip_file(str(original_file), temp_file.name)
        response1 = call_api(client, str(temp_file.name), "application/gzip", {"gz_uncompressed_content_type": gz_uncompressed_content_type})

    response2 = call_api(client, str(original_file), gz_uncompressed_content_type, {})

    diff = DeepDiff(t1=response1.json(), t2=response2.json(),
                    exclude_regex_paths=r"root\[\d+\]\['metadata'\]\['filename'\]")
    assert len(diff) == 0
