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

    We use the library's detect_filetype to identify the file. If we can't partition it, return a 400 error.
    """
    content_type = _remove_optional_info_from_mime_type(file.content_type)
    filetype = FileType.from_mime_type(content_type)

    # If content_type was not specified, use the library to identify the file
    # We inspect the bytes to do this, so we need to buffer the file
    if not filetype or filetype == FileType.UNK:
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
