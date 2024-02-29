import gzip
import shutil
import io
import tempfile
from pathlib import Path
from typing import List

import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from deepdiff import DeepDiff

from prepline_general.api.app import app

MAIN_API_ROUTE = "general/v0/general"


@pytest.mark.parametrize("output_format", ["application/json", "text/csv"])
@pytest.mark.parametrize(
    "example_filenames, uncompressed_content_type",
    [
        (["fake-html.html"], "text/html"),
        (["stanley-cups.csv"], "application/csv"),
        (["fake.doc"], "application/msword"),
        (["layout-parser-paper-fast.pdf"], "application/pdf"),
        (["fake-email-attachment.eml", "fake-email.eml"], "message/rfc822"),
        (
            ["fake-email-attachment.eml", "fake-email.eml", "fake-email-image-embedded.eml"],
            "message/rfc822",
        ),
        (["layout-parser-paper-fast.pdf", "list-item-example.pdf"], "application/pdf"),
        # now the same but without explicit content type
        # to make the system guess the un-gzipped type based on content.
        (["fake-html.html"], ""),
        (["fake-email-attachment.eml", "fake-email.eml"], ""),
        (["layout-parser-paper-fast.pdf", "list-item-example.pdf"], ""),
        # case with already gzipped file
    ],
)
def test_multiple_gzipped_file_is_parsed_same_as_original_explicit_gz_type(
    output_format: str, example_filenames: List[str], uncompressed_content_type: str
):
    """
    Verify that API supports unzipping gzip and correctly interprets gz_uncompressed_content_type
    by comparing response to directly parsing the same files.
    The one thing which changes is the filenames in metadata, which have to be ignored.
    """

    client = TestClient(app)
    gz_options = {
        "gz_uncompressed_content_type": (
            uncompressed_content_type if uncompressed_content_type else None
        ),
        "output_format": output_format,
    }
    # Gzips the example_filenames into temporary file and sends to API
    response1 = get_gzipped_response(client, example_filenames, gz_options)
    # Sends original files to API
    response2 = call_api(
        client, example_filenames, uncompressed_content_type, {"output_format": output_format}
    )
    compare_responses(response1, response2, output_format, len(example_filenames))


def compare_responses(
    response1: httpx.Response, response2: httpx.Response, output_format: str, files_count: int
) -> None:
    if output_format == "application/json":
        if files_count == 1:
            exclude_regex_paths = r"root\[\d+\]\['metadata'\]\['filename'\]"
        else:
            exclude_regex_paths = r"root\[\d+\]\[\d+\]\['metadata'\]\['filename'\]"
        diff = DeepDiff(
            t1=response1.json(),
            t2=response2.json(),
            exclude_regex_paths=exclude_regex_paths,
        )
        assert len(diff) == 0
    else:
        df1 = pd.read_csv(io.StringIO(response1.text))
        df2 = pd.read_csv(io.StringIO(response2.text))
        diff = DeepDiff(
            t1=df1.to_dict(), t2=df2.to_dict(), exclude_regex_paths=r"root\['filename'\]\[\d+\]"
        )
        assert len(diff) == 0


def call_api(
    client: TestClient, filenames: List[str], content_type: str, options: dict
) -> httpx.Response:
    ff = []
    for filename in filenames:
        full_path = Path("sample-docs") / filename
        ff.append(("files", (str(full_path), open(full_path, "rb"), content_type)))

    response = client.post(
        MAIN_API_ROUTE,
        files=ff,
        data=options,
    )
    assert response.status_code == 200, response.text
    assert len(response.text) > 0
    return response


def get_gzipped_response(client: TestClient, filenames: List[str], options: dict) -> httpx.Response:
    tempfiles = {}
    for filename in filenames:
        gz_file_extension = f".{Path(filename).suffix}.gz"
        temp_file = tempfile.NamedTemporaryFile(suffix=gz_file_extension)
        full_path = Path("sample-docs") / filename
        gzip_file(str(full_path), temp_file.name)
        tempfiles[filename] = temp_file

    response = call_api(
        client, [temp_file.name for temp_file in tempfiles.values()], "application/gzip", options
    )

    for filename in filenames:
        tempfiles[filename].close()

    return response


def gzip_file(in_filepath: str, out_filepath: str):
    with open(in_filepath, "rb") as f_in:
        with gzip.open(out_filepath, "wb", compresslevel=1) as f_out:
            shutil.copyfileobj(f_in, f_out)
