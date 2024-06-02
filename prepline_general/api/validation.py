from __future__ import annotations

import mimetypes
import os

from typing import IO, Optional

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError
from unstructured_inference.models.chipper import MODEL_TYPES as CHIPPER_MODEL_TYPES


def _check_pdf(file: IO[bytes]):
    """Check if the PDF file is encrypted, otherwise assume it is not a valid PDF."""
    try:
        pdf = PdfReader(file)

        # This will raise if the file is encrypted
        pdf.metadata
        return pdf
    except FileNotDecryptedError:
        raise HTTPException(
            status_code=400,
            detail="File is encrypted. Please decrypt it with password.",
        )
    except PdfReadError:
        raise HTTPException(status_code=422, detail="File does not appear to be a valid PDF")


def _validate_strategy(strategy: str) -> str:
    strategy = strategy.lower()
    strategies = ["fast", "hi_res", "auto", "ocr_only"]
    if strategy not in strategies:
        raise HTTPException(
            status_code=400, detail=f"Invalid strategy: {strategy}. Must be one of {strategies}"
        )
    return strategy


def _validate_hi_res_model_name(
    hi_res_model_name: Optional[str], show_coordinates: bool
) -> Optional[str]:
    # Make sure chipper aliases to the latest model
    if hi_res_model_name and hi_res_model_name == "chipper":
        hi_res_model_name = "chipperv2"

    if hi_res_model_name and hi_res_model_name in CHIPPER_MODEL_TYPES and show_coordinates:
        raise HTTPException(
            status_code=400,
            detail=f"coordinates aren't available when using the {hi_res_model_name} model type",
        )
    return hi_res_model_name


def _validate_chunking_strategy(chunking_strategy: Optional[str]) -> Optional[str]:
    """Raise on `chunking_strategy` is not a valid chunking strategy name.

    Also provides case-insensitivity.
    """
    if chunking_strategy is None:
        return None

    chunking_strategy = chunking_strategy.lower()
    available_strategies = ["basic", "by_title"]

    if chunking_strategy not in available_strategies:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid chunking strategy: {chunking_strategy}. Must be one of"
                f" {available_strategies}"
            ),
        )

    return chunking_strategy


def get_validated_mimetype(file: UploadFile) -> Optional[str]:
    """The MIME-type of `file`.

    The mimetype is computed based on `file.content_type`, or the mimetypes lib if that's too
    generic. If the user has set UNSTRUCTURED_ALLOWED_MIMETYPES, validate against this list and
    return HTTP 400 for an invalid type.
    """
    content_type = file.content_type
    filename = str(file.filename)  # -- "None" when file.filename is None --
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(filename)[0]

        # Some filetypes missing for this library, just hardcode them for now
        if not content_type:
            if filename.endswith(".md"):
                content_type = "text/markdown"
            elif filename.endswith(".msg"):
                content_type = "message/rfc822"

    allowed_mimetypes_str = os.environ.get("UNSTRUCTURED_ALLOWED_MIMETYPES")
    if allowed_mimetypes_str is not None:
        allowed_mimetypes = allowed_mimetypes_str.split(",")

        if content_type not in allowed_mimetypes:
            raise HTTPException(
                status_code=400,
                detail=(f"File type {content_type} is not supported."),
            )

    return content_type
