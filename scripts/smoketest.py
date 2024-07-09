import io
import os
import time
import gzip
import shutil
from pathlib import Path
from typing import List, Optional
import tempfile

import pytest
import requests
import pandas as pd

API_URL = "http://localhost:8000/general/v0/general"
# NOTE(rniko): Skip inference tests if we're running on an emulated architecture
skip_inference_tests = os.getenv("SKIP_INFERENCE_TESTS", "").lower() in {"true", "yes", "y", "1"}


def send_document(
    filenames: List[str],
    filenames_gzipped: Optional[List[str]] = None,
    content_type: str = "",
    strategy: str = "auto",
    output_format: str = "application/json",
    skip_infer_table_types: list[str] = [],
    uncompressed_content_type: str = "",
):
    if filenames_gzipped is None:
        filenames_gzipped = []
    files = []
    for filename in filenames:
        files.append(("files", (str(filename), open(filename, "rb"), content_type)))
    for filename in filenames_gzipped:
        files.append(("files", (str(filename), open(filename, "rb"), "application/gzip")))

    options = {
        "strategy": strategy,
        "output_format": output_format,
        "skip_infer_table_types": skip_infer_table_types,
    }
    if uncompressed_content_type:
        options["gz_uncompressed_content_type"] = uncompressed_content_type

    return requests.post(
        API_URL,
        files=files,
        data=options,
    )


@pytest.mark.parametrize(
    ("extension", "example_filename", "content_type"),
    [
        (".bmp", "DA-1p.bmp", "image/bmp"),
        (".csv", "stanley-cups.csv", "application/csv"),
        (".doc", "fake.doc", "application/msword"),
        (
            ".docx",
            "fake.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (".eml", "fake-email-attachment.eml", "message/rfc822"),
        (".epub", "winter-sports.epub", "application/epub"),
        (".heic", "DA-1p.heic", "image/heic"),
        (".html", "fake-html.html", "text/html"),
        (".jpeg", "layout-parser-paper-fast.jpg", "image/jpeg"),
        (".md", "README.md", "text/markdown"),
        (".msg", "fake-email.msg", "application/x-ole-storage"),
        (".odt", "fake.odt", "application/vnd.oasis.opendocument.text"),
        (".pdf", "layout-parser-paper.pdf", "application/pdf"),
        (".png", "english-and-korean.png", "image/png"),
        (".ppt", "fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            ".pptx",
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        (".rst", "README.rst", "text/prs.fallenstein.rst"),
        (".rtf", "fake-doc.rtf", "application/rtf"),
        (".tiff", "layout-parser-paper-fast.tiff", "image/tiff"),
        (".tsv", "stanley-cups.tsv", "text/tab-separated-values"),
        (".txt", "fake-text.txt", "text/plain"),
        (
            ".xlsx",
            "stanley-cups.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (".xml", "fake-xml.xml", "text/xml"),
        (".json", "spring-weather.html.json", "application/json"),
        (
            ".gz",
            "layout-parser-paper.pdf.gz",
            "application/gzip",
        ),
    ],
)
def test_happy_path_all_types(extension, example_filename: str, content_type: str):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    # The auto strategy will run ocr on these files
    # This doesn't always work on our macs
    if skip_inference_tests and extension in [
        ".bmp",
        ".heic",
        ".jpeg",
        ".pdf",
        ".png",
        ".tiff",
        ".gz",  # Since we're using a gzipped pdf...
    ]:
        pytest.skip("emulated hardware")

    test_file = str(Path("sample-docs") / example_filename)

    # Verify we can send with explicit content type
    response = send_document(filenames=[test_file], content_type=content_type)

    if response.status_code != 200:
        assert False, response.text

    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20

    # Verify we can infer the filetype on the server
    response = send_document(filenames=[test_file], content_type=None)

    if response.status_code != 200:
        assert False, response.text

    assert len(response.json()) > 0
    assert len("".join(elem["text"] for elem in response.json())) > 20

    json_response = response

    # Verify we can set output type to csv
    csv_response = send_document(
        filenames=[test_file],
        content_type=content_type,
        output_format="text/csv",
    )
    assert csv_response.status_code == 200
    assert len(csv_response.text) > 0
    df = pd.read_csv(io.StringIO(csv_response.text))
    assert len(df) == len(json_response.json())


@pytest.mark.parametrize("output_format", ["application/json", "text/csv"])
@pytest.mark.parametrize(
    "filenames_to_gzip, filenames_verbatim, uncompressed_content_type",
    [
        (["fake-html.html"], [], "text/html"),
        (["stanley-cups.csv"], [], "application/csv"),
        (["fake.doc"], [], "application/msword"),
        # compressed and uncompressed
        pytest.param(
            ["layout-parser-paper-fast.pdf"],
            ["list-item-example.pdf"],
            "application/pdf",
            marks=pytest.mark.skipif(skip_inference_tests, reason="emulated architecture"),
        ),
        (["fake-email.eml"], ["fake-email-image-embedded.eml"], "message/rfc822"),
        # compressed and uncompressed
        # empty content-type means that API should detect filetype after decompressing.
        pytest.param(
            ["layout-parser-paper-fast.pdf"],
            ["list-item-example.pdf"],
            "",
            marks=pytest.mark.skipif(skip_inference_tests, reason="emulated architecture"),
        ),
        (["fake-email.eml"], ["fake-email-image-embedded.eml"], ""),
    ],
)
def test_gzip_sending(
    output_format: str,
    filenames_to_gzip: List[str],
    filenames_verbatim: List[str],
    uncompressed_content_type: str,
):
    temp_files = {}

    for filename in filenames_to_gzip:
        gz_file_extension = f"{Path(filename).suffix}.gz"
        temp_file = tempfile.NamedTemporaryFile(suffix=gz_file_extension)
        full_path = Path("sample-docs") / filename
        gzip_file(str(full_path), temp_file.name)
        temp_files[filename] = temp_file
    filenames_gzipped = [temp_file.name for temp_file in temp_files.values()]

    filenames = []
    for filename in filenames_verbatim:
        filenames.append(str(Path("sample-docs") / filename))

    json_response = send_document(
        filenames,
        filenames_gzipped,
        content_type=uncompressed_content_type,
        uncompressed_content_type=uncompressed_content_type,
    )
    assert json_response.status_code == 200, json_response.text
    json_content = json_response.json()
    assert len(json_content) > 0
    if len(filenames_gzipped + filenames) > 1:
        for file in json_content:
            assert len("".join(elem["text"] for elem in file)) > 20
    else:
        assert len("".join(elem["text"] for elem in json_content)) > 20

    csv_response = send_document(
        filenames,
        filenames_gzipped,
        content_type=uncompressed_content_type,
        uncompressed_content_type=uncompressed_content_type,
        output_format="text/csv",
    )
    assert csv_response.status_code == 200
    assert len(csv_response.text) > 0
    df = pd.read_csv(io.StringIO(csv_response.text))
    if len(filenames_gzipped + filenames) > 1:
        json_size = 0
        for file in json_content:
            json_size += len(file)
        assert len(df) == json_size
    else:
        assert len(df) == len(json_content)

    for filename in filenames_to_gzip:
        temp_files[filename].close()


@pytest.mark.skipif(skip_inference_tests, reason="emulated architecture")
def test_strategy_performance():
    """
    For the files in sample-docs, verify that the fast strategy
    is significantly faster than the hi_res strategy
    """
    performance_ratio = 4
    test_file = str(Path("sample-docs") / "layout-parser-paper.pdf")

    start_time = time.monotonic()
    response = send_document(
        filenames=[test_file], content_type="application/pdf", strategy="hi_res"
    )
    hi_res_time = time.monotonic() - start_time
    assert response.status_code == 200

    start_time = time.monotonic()
    response = send_document(filenames=[test_file], content_type="application/pdf", strategy="fast")
    fast_time = time.monotonic() - start_time
    assert response.status_code == 200
    assert hi_res_time > performance_ratio * fast_time


@pytest.mark.skipif(skip_inference_tests, reason="emulated architecture")
@pytest.mark.parametrize(
    "strategy, skip_infer_table_types, expected_table_num",
    [
        ("fast", [], 0),
        ("fast", ["pdf"], 0),
        ("hi_res", [], 2),
        ("hi_res", ["pdf"], 0),
    ],
)
def test_table_support(strategy: str, skip_infer_table_types: list[str], expected_table_num: int):
    """
    Test that table extraction works on hi_res strategy
    """
    test_file = str(Path("sample-docs") / "layout-parser-paper.pdf")
    response = send_document(
        filenames=[test_file],
        content_type="application/pdf",
        strategy=strategy,
        skip_infer_table_types=skip_infer_table_types,
    )

    assert response.status_code == 200
    extracted_tables = [
        el["metadata"]["text_as_html"]
        for el in response.json()
        if "text_as_html" in el["metadata"].keys()
    ]
    assert len(extracted_tables) == expected_table_num
    if expected_table_num > 0:
        # Test a text form a table is extracted
        # Note(austin) - table output has changed - this line isn't returned
        # assert "Layouts of scanned modern magazines and scientific reports" in extracted_tables[0]
        assert "Layouts of history" in extracted_tables[0]


def gzip_file(in_filepath: str, out_filepath: str):
    with open(in_filepath, "rb") as f_in:
        with gzip.open(out_filepath, "wb", compresslevel=1) as f_out:
            shutil.copyfileobj(f_in, f_out)
