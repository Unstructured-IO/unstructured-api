import os
import tempfile
import time
from pathlib import Path

import pytest
import requests
import pandas as pd
import io
import ast
from unstructured.partition.auto import partition
from unstructured.staging.base import convert_to_csv, convert_to_isd, dict_to_elements

API_URL = "http://localhost:8000/general/v0/general"
# NOTE(rniko): Skip inference tests if we're running on an emulated architecture
skip_inference_tests = os.getenv("SKIP_INFERENCE_TESTS", "").lower() in {"true", "yes", "y", "1"}


def send_document(
    filename,
    content_type,
    strategy="fast",
    output_format="application/json",
    pdf_infer_table_structure="false",
):
    # Note: `content_type` is not passed into request since fast API will overwrite it.
    if str(filename).endswith(".gz"):
        files = {"files": (str(filename), open(filename, "rb"), "application/gzip")}
    else:
        files = {"files": (str(filename), open(filename, "rb"))}
    return requests.post(
        API_URL,
        files=files,
        data={
            "strategy": strategy,
            "output_format": output_format,
            "pdf_infer_table_structure": pdf_infer_table_structure,
        },
    )


@pytest.mark.parametrize(
    "example_filename, content_type, output_format, strategy",
    [
        # Note(yuming): Please sort filetypes alphabetically according to
        # https://github.com/Unstructured-IO/unstructured/blob/main/unstructured/partition/auto.py#L14
        ("stanley-cups.csv", "application/csv"),
        ("fake.doc", "application/msword"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("alert.eml", "message/rfc822"),
        ("announcement.eml", "message/rfc822"),
        ("fake-email-attachment.eml", "message/rfc822"),
        ("fake-email-image-embedded.eml", "message/rfc822"),
        ("fake-email.eml", "message/rfc822"),
        ("family-day.eml", "message/rfc822"),
        ("winter-sports.epub", "application/epub"),
        ("fake-html.html", "text/html"),
        pytest.param(
            "layout-parser-paper-fast.jpg",
            "image/jpeg",
            marks=pytest.mark.skipif(skip_inference_tests, reason="emulated architecture"),
        ),
        ("spring-weather.html.json", "application/json"),
        ("README.md", "text/markdown"),
        ("fake-email.msg", "application/x-ole-storage"),
        ("fake.odt", "application/vnd.oasis.opendocument.text"),
        ("alert.eml", "message/rfc822", "application/json", "fast"),
        ("announcement.eml", "message/rfc822", "application/json", "fast"),
        ("fake-email-attachment.eml", "message/rfc822", "application/json", "fast"),
        ("fake-email-image-embedded.eml", "message/rfc822", "application/json", "fast"),
        ("fake-email.eml", "message/rfc822", "application/json", "fast"),
        ("fake-html.html", "text/html", "application/json", "fast"),
        ("fake-power-point.ppt", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/json", "fast"),
        ("fake-text.txt", "text/plain", "application/json", "fast"),
        ("fake.doc", "application/msword", "application/json", "fast"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/json", "fast"),
        ("family-day.eml", "message/rfc822", "application/json", "fast"),
        ("winter-sports.epub", "application/epub", "application/json", "fast"),
        ("fake-doc.rtf", "application/rtf", "application/json", "fast"),
        ("fake.odt", "application/vnd.oasis.opendocument.text", "application/json", "fast"),
        ("stanley-cups.csv", "application/csv", "application/json", "fast"),
        pytest.param("fake-excel.xlsx", None, "application/json", "fast", marks=pytest.mark.xfail(reason="not supported yet")),
        # Note(austin) The two inference calls will hang on mac with unsupported hardware error
        # Skip these with SKIP_INFERENCE_TESTS=true make docker-test
        pytest.param(
            "layout-parser-paper.pdf",
            "application/pdf",
            marks=pytest.mark.skipif(skip_inference_tests, reason="emulated architecture"),
        ),
        ("fake-power-point.ppt", "application/vnd.ms-powerpoint"),
        (
            "fake-power-point.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        ("README.rst", "text/prs.fallenstein.rst"),
        ("fake-doc.rtf", "application/rtf"),
        ("fake-text.txt", "text/plain"),
        ("stanley-cups.tsv", "text/tab-separated-values"),
        (
            "stanley-cups.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        pytest.param("layout-parser-paper.pdf", "application/pdf", "application/json", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg", "image/jpeg", "application/json", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        ("fake-text.txt", "text/plain", "text/csv", "fast"),
        ("announcement.eml", "message/rfc822", "text/csv", "fast"),
        ("fake-email-attachment.eml", "message/rfc822", "text/csv", "fast"),
        ("fake-email-image-embedded.eml", "message/rfc822", "text/csv", "fast"),
        ("fake-email.eml", "message/rfc822", "text/csv", "fast"),
        ("fake-html.html", "text/html", "text/csv", "fast"),
        ("fake-power-point.ppt", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "text/csv", "fast"),
        ("fake.doc", "application/msword", "text/csv", "fast"),
        ("fake.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/csv", "fast"),
        ("family-day.eml", "message/rfc822", "text/csv", "fast"),
        ("winter-sports.epub", "application/epub", "text/csv", "fast"),
        ("fake-doc.rtf", "application/rtf", "text/csv", "fast"),
        ("fake.odt", "application/vnd.oasis.opendocument.text", "text/csv", "fast"),
        ("stanley-cups.csv", "application/csv", "text/csv", "fast"),
        pytest.param("fake-excel.xlsx", None, "text/csv", "fast", marks=pytest.mark.xfail(reason="not supported yet")),
        pytest.param("layout-parser-paper.pdf", "application/pdf", "text/csv", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg", "image/jpeg", "text/csv", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        ("fake-text.txt.gz", "text/plain", "application/json", "fast"),
        ("announcement.eml.gz", "message/rfc822", "application/json", "fast"),
        ("fake-email-attachment.eml.gz", "message/rfc822", "application/json", "fast"),
        ("fake-email-image-embedded.eml.gz", "message/rfc822", "application/json", "fast"),
        ("fake-email.eml.gz", "message/rfc822", "application/json", "fast"),
        ("fake-html.html.gz", "text/html", "application/json", "fast"),
        ("fake-power-point.ppt.gz", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/json", "fast"),
        ("fake.doc.gz", "application/msword", "application/json", "fast"),
        ("fake.docx.gz", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/json", "fast"),
        ("family-day.eml.gz", "message/rfc822", "application/json", "fast"),
        ("winter-sports.epub.gz", "application/epub", "application/json", "fast"),
        ("fake-doc.rtf.gz", "application/rtf", "application/json", "fast"),
        ("fake.odt.gz", "application/vnd.oasis.opendocument.text", "application/json", "fast"),
        ("stanley-cups.csv.gz", "application/csv", "application/json", "fast"),
        pytest.param("fake-excel.xlsx.gz", None, "application/json", "fast", marks=pytest.mark.xfail(reason="not supported yet")),
        pytest.param("layout-parser-paper.pdf.gz", "application/pdf", "application/json", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        pytest.param("layout-parser-paper-fast.jpg.gz", "image/jpeg", "text/csv", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        ("fake-text.txt.gz", "text/plain", "text/csv", "fast"),
        ("announcement.eml.gz", "message/rfc822", "text/csv", "fast"),
        ("fake-email-attachment.eml.gz", "message/rfc822", "text/csv", "fast"),
        ("fake-email-image-embedded.eml.gz", "message/rfc822", "text/csv", "fast"),
        ("fake-email.eml.gz", "message/rfc822", "text/csv", "fast"),
        ("fake-html.html.gz", "text/html", "text/csv", "fast"),
        ("fake-power-point.ppt.gz", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "text/csv", "fast"),
        ("fake.doc.gz", "application/msword", "text/csv", "fast"),
        ("fake.docx.gz", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/csv", "fast"),
        ("family-day.eml.gz", "message/rfc822", "text/csv", "fast"),
        ("winter-sports.epub.gz", "application/epub", "text/csv", "fast"),
        ("fake-doc.rtf.gz", "application/rtf", "text/csv", "fast"),
        ("fake.odt.gz", "application/vnd.oasis.opendocument.text", "text/csv", "fast"),
        ("stanley-cups.csv", "application/csv", "text/csv", "fast"),
        pytest.param("fake-excel.xlsx.gz", None, "text/csv", "fast", marks=pytest.mark.xfail(reason="not supported yet")),
        pytest.param("layout-parser-paper.pdf.gz", "application/pdf", "text/csv", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
        ("fake-xml.xml", "text/xml"),
    ],
        pytest.param("layout-parser-paper-fast.jpg.gz", "image/jpeg", "text/csv", "fast", marks=pytest.mark.skipif(
            skip_inference_tests, reason="emulated architecture")
        ),
    ]
)
def test_happy_path(example_filename, content_type, output_format, strategy):
    """
    For the files in sample-docs, verify that we get a 200
    and some structured response
    """
    test_file = Path("sample-docs") / example_filename
    json_response = send_document(test_file, content_type)
    response = send_document(
        filename=test_file,
        strategy=strategy,
        content_type=content_type,
        output_format=output_format,
    )

    assert json_response.status_code == 200
    assert len(json_response.json()) > 0
    assert len("".join(elem["text"] for elem in json_response.json())) > 20

    csv_response = send_document(test_file, content_type, output_format="text/csv")
    assert csv_response.status_code == 200
    assert len(csv_response.text) > 0
    df = pd.read_csv(io.StringIO(ast.literal_eval(csv_response.text)))
    assert len(df) == len(json_response.json())
    assert(response.status_code == 200)
    assert len(response.json()) > 0
    if output_format == "text/csv":
        # NOTE(kravetsmic): looks like a bug on macOS (m1), incorrectly scanned text from images and pdf files
        if example_filename not in [
                "layout-parser-paper.pdf",
                "layout-parser-paper-fast.jpg",
                "layout-parser-paper.pdf.gz",
                "layout-parser-paper-fast.jpg.gz"
            ]:
            if str(test_file).endswith(".gz"):
                test_file = Path("sample-docs") / example_filename[:-3]
            with open(test_file, "rb") as file:
                # NOTE(kravetsmic): passing file as parameter raised zipfile.BadZipFile: File is not a zip file
                if str(test_file).endswith(".ppt"):
                    elements = partition(str(test_file), strategy=strategy)
                else:
                    elements = partition(
                        file=file,
                        file_filename=str(test_file),
                        content_type=content_type,
                        strategy=strategy
                    )
            result = convert_to_isd(elements)
            for element in result:
                element['metadata']['filename'] = os.path.basename(str(test_file))
                del element['coordinates']
            elements = dict_to_elements(result)
            assert response.json() == convert_to_csv(elements)
    else:
        assert len("".join(elem["text"] for elem in response.json())) > 20


@pytest.mark.skipif(skip_inference_tests, reason="emulated architecture")
def test_strategy_performance():
    """
    For the files in sample-docs, verify that the fast strategy
    is significantly faster than the hi_res strategy
    """
    performance_ratio = 4
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"

    start_time = time.time()
    response = send_document(test_file, content_type="application/pdf", strategy="hi_res")
    hi_res_time = time.time() - start_time
    assert response.status_code == 200

    start_time = time.time()
    response = send_document(test_file, content_type="application/pdf", strategy="fast")
    fast_time = time.time() - start_time
    assert response.status_code == 200

    assert hi_res_time > performance_ratio * fast_time


@pytest.mark.skipif(skip_inference_tests, reason="emulated architecture")
@pytest.mark.parametrize(
    "strategy, pdf_infer_table_structure, expected_table_num",
    [
        ("fast", "True", 0),
        ("fast", "False", 0),
        ("hi_res", "True", 2),
        ("hi_res", "False", 0),
    ],
)
def test_table_support(strategy, pdf_infer_table_structure, expected_table_num):
    """
    Test that table extraction works on hi_res strategy
    """
    test_file = Path("sample-docs") / "layout-parser-paper.pdf"
    response = send_document(
        test_file,
        "application/pdf",
        strategy=strategy,
        pdf_infer_table_structure=pdf_infer_table_structure,
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
        assert "Layouts of scanned modern magazines and scientific reports" in extracted_tables[0]
