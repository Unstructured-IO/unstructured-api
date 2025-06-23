import os
from typing import Optional
from io import BytesIO

from fastapi import HTTPException, UploadFile

from unstructured.file_utils.filetype import detect_filetype
from unstructured.file_utils.model import FileType


def _remove_optional_info_from_mime_type(content_type: str | None) -> str | None:
    """removes charset information from mime types, e.g.,
    "application/json; charset=utf-8" -> "application/json"
    """
    if not content_type:
        return content_type
    return content_type.split(";")[0]


def get_validated_mimetype(file: UploadFile) -> Optional[str]:
    """Given the incoming file, identify and return the correct mimetype.

    Always inspects the actual file bytes to determine the true file type,
    ignoring client-provided Content-Type headers which can be misleading.

    Once we have a filteype, check is_partitionable and return 400 if we don't support this file.
    """
    file_buffer = BytesIO(file.file.read())
    file.file.seek(0)
    file_buffer.name = file.filename
    filetype = detect_filetype(file=file_buffer)

    if not filetype.is_partitionable:
        raise HTTPException(
            status_code=400,
            detail=(f"File type {filetype.mime_type} is not supported."),
        )

    return filetype.mime_type
