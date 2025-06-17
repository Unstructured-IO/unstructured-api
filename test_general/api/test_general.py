from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi import HTTPException
from pypdf import PdfReader

from prepline_general.api.general import _check_pdf

TEST_ASSETS_DIR = Path(__file__).parent.parent.parent / "sample-docs"


def _open_pdf(pdf_path: str) -> io.BytesIO:
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    return io.BytesIO(pdf_content)


def test_check_pdf_with_valid_pdf():
    pdf_path = str(TEST_ASSETS_DIR / "list-item-example.pdf")
    pdf = _open_pdf(pdf_path)

    result = _check_pdf(pdf)
    assert isinstance(result, PdfReader)


@pytest.mark.parametrize(
    ("pdf_name", "expected_error_message"),
    [
        ("failing-encrypted.pdf", "File is encrypted. Please decrypt it with password."),
        (
            "failing-invalid.pdf",
            "File does not appear to be a valid PDF. Error: Stream has ended unexpectedly",
        ),
        (
            "failing-missing-root.pdf",
            "File does not appear to be a valid PDF. Error: Cannot find Root object in pdf",
        ),
        (
            "failing-missing-pages.pdf",
            "File does not appear to be a valid PDF. Error: Invalid object in /Pages",
        ),
    ],
)
def test_check_pdf_with_invalid_pdf(pdf_name: str, expected_error_message: str):
    pdf_path = str(TEST_ASSETS_DIR / pdf_name)
    pdf = _open_pdf(pdf_path)

    with pytest.raises(HTTPException) as exc_info:
        _check_pdf(pdf)

    assert exc_info.value.status_code == 422
    assert expected_error_message == str(exc_info.value.detail)
