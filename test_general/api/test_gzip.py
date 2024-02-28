import gzip
import shutil
import io
import tempfile
from pathlib import Path

import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from deepdiff import DeepDiff

from prepline_general.api.app import app

MAIN_API_ROUTE = "general/v0/general"


@pytest.mark.parametrize("output_format", ["application/json", "text/csv"])
@pytest.mark.parametrize(
    "example_filename, uncompressed_content_type",
    [
        ("fake-html.html", "text/html"),
        ("stanley-cups.csv", "application/csv"),
        ("fake.doc", "application/msword"),
        ("layout-parser-paper-fast.pdf", "application/pdf"),
        # now the same but without explicit content type to make the system guess the un-gzipped type based on content.
        ("fake-html.html", ""),
        ("stanley-cups.csv", ""),
        ("fake.doc", ""),
        ("layout-parser-paper-fast.pdf", ""),
    ],
)
def test_single_gzipped_file_is_parsed_same_as_original_explicit_gz_type(
    output_format: str, example_filename: str, uncompressed_content_type: str
):
    """
    Verify that API supports unzipping gzip and correctly interprets gz_uncompressed_content_type
    by comparing response to directly parsing the same file.
    """

    original_file = Path("sample-docs") / example_filename
    client = TestClient(app)
    gz_options = {
        "gz_uncompressed_content_type": (
            uncompressed_content_type if uncompressed_content_type else None
        ),
        "output_format": output_format,
    }

    response1 = get_gzipped_response(client, str(original_file), gz_options)
    response2 = call_api(
        client, str(original_file), uncompressed_content_type, {"output_format": output_format}
    )
    compare_responses(response1, response2, output_format)


def compare_responses(
    response1: httpx.Response, response2: httpx.Response, output_format: str
) -> None:
    if output_format == "application/json":
        diff = DeepDiff(
            t1=response1.json(),
            t2=response2.json(),
            exclude_regex_paths=r"root\[\d+\]\['metadata'\]\['filename'\]",
        )
        assert len(diff) == 0
    else:
        df1 = pd.read_csv(io.StringIO(response1.text))
        df2 = pd.read_csv(io.StringIO(response2.text))
        diff = DeepDiff(
            t1=df1.to_dict(), t2=df2.to_dict(), exclude_regex_paths=r"root\['filename'\]\[\d+\]"
        )
        assert len(diff) == 0


def call_api(client: TestClient, filename: str, content_type: str, options: dict) -> httpx.Response:
    response = client.post(
        MAIN_API_ROUTE,
        files=[("files", (str(filename), open(filename, "rb"), content_type))],
        data=options,
    )
    assert response.status_code == 200, response.text
    assert len(response.text) > 0
    return response


def get_gzipped_response(client: TestClient, original_file: str, options: dict) -> httpx.Response:
    gz_file_extension = f".{Path(original_file).suffix}.gz"
    with tempfile.NamedTemporaryFile(suffix=gz_file_extension) as temp_file:
        gzip_file(str(original_file), temp_file.name)
        response = call_api(client, str(temp_file.name), "application/gzip", options)
        return response


def gzip_file(in_filepath: str, out_filepath: str):
    with open(in_filepath, "rb") as f_in:
        with gzip.open(out_filepath, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
