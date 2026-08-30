from typing import IO, Any, Optional, cast

from fastapi import HTTPException, UploadFile

from unstructured.file_utils.filetype import detect_filetype
from unstructured.file_utils.model import FileType


class _SpooledFileProxy:
    """Expose a spooled upload as a normal file without copying its complete body.

    `unstructured.detect_filetype()` copies `SpooledTemporaryFile` inputs into a `BytesIO`, even
    though its detector only seeks and reads small portions. Hiding the concrete type preserves the
    normal file interface while avoiding that document-sized allocation.

    `name` is set explicitly rather than forwarded: the detector reads `.name` to derive the
    filename-extension, and a spooled file's own `.name` is the temporary file rather than the
    uploaded filename.
    """

    def __init__(self, file: IO[bytes], name: str | None):
        self._file = file
        self.name = name

    def __getattr__(self, name: str) -> Any:
        return getattr(self._file, name)


def _remove_optional_info_from_mime_type(content_type: str | None) -> str | None:
    """removes charset information from mime types, e.g.,
    "application/json; charset=utf-8" -> "application/json"
    """
    if not content_type:
        return content_type
    return content_type.split(";")[0]


def get_validated_mimetype(file: UploadFile, content_type_hint: str | None = None) -> Optional[str]:
    """Given the incoming file, identify and return the correct mimetype.

    Order of operations:
    - If user passed content_type as a form param, take it as truth.
    - Otherwise, use file.content_type (as set by the Content-Type header)
    - If no content_type was passed and the header wasn't useful, call the library's detect_filetype

    Once we have a filteype, check is_partitionable and return 400 if we don't support this file.
    """
    content_type: str | None = None

    if content_type_hint is not None:
        content_type = content_type_hint
    else:
        content_type = _remove_optional_info_from_mime_type(file.content_type)

    filetype = FileType.from_mime_type(content_type)

    # If content_type was not specified, use the library to identify the file
    # The detector seeks and reads bounded portions of the upload. Proxy the spooled file so the
    # dependency does not make a complete in-memory `BytesIO` copy first.
    if not filetype or filetype == FileType.UNK:
        file_proxy = cast(IO[bytes], _SpooledFileProxy(file.file, file.filename))
        try:
            filetype = detect_filetype(file=file_proxy)
        finally:
            file.file.seek(0)

    if not filetype.is_partitionable:
        raise HTTPException(
            status_code=400,
            detail=(f"File type {filetype.mime_type} is not supported."),
        )

    return filetype.mime_type
