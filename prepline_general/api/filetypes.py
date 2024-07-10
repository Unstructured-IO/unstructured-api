import mimetypes
import os
from fastapi import UploadFile, HTTPException
from typing import Optional

DEFAULT_MIMETYPES = (
    "application/pdf,application/msword,image/jpeg,image/png,text/markdown,"
    "text/x-markdown,text/html,"
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
    "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument."
    "presentationml.presentation,"
    "application/json,"
    "application/vnd.ms-powerpoint,"
    "text/html,message/rfc822,text/plain,image/png,"
    "application/epub,application/epub+zip,"
    "application/rtf,text/rtf,"
    "application/vnd.oasis.opendocument.text,"
    "text/csv,text/x-csv,application/csv,application/x-csv,"
    "text/comma-separated-values,text/x-comma-separated-values,"
    "application/xml,text/xml,text/x-rst,text/prs.fallenstein.rst,"
    "text/tsv,text/tab-separated-values,"
    "application/x-ole-storage,application/vnd.ms-outlook,"
    "application/yaml,"
    "application/x-yaml,"
    "text/x-yaml,"
    "text/yaml,"
    "image/bmp,"
    "image/heic,"
    "image/tiff,"
    "text/org,"
)

if not os.environ.get("UNSTRUCTURED_ALLOWED_MIMETYPES", None):
    os.environ["UNSTRUCTURED_ALLOWED_MIMETYPES"] = DEFAULT_MIMETYPES


def _load_mimetypes() -> None:
    """Call this on startup to ensure that all expected file extensions are present in the mimetypes
    lib"""
    expected_mimetypes = [
        (".bmp", "image/bmp"),
        (".csv", "application/csv"),
        (".doc", "application/msword"),
        (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (".eml", "message/rfc822"),
        (".epub", "application/epub"),
        (".gz", "application/gzip"),
        (".heic", "image/heic"),
        (".html", "text/html"),
        (".jpeg", "image/jpeg"),
        (".jpg", "image/jpeg"),
        (".json", "application/json"),
        (".md", "text/markdown"),
        (".msg", "application/x-ole-storage"),
        (".odt", "application/vnd.oasis.opendocument.text"),
        (".org", "text/org"),
        (".pdf", "application/pdf"),
        (".png", "image/png"),
        (".ppt", "application/vnd.ms-powerpoint"),
        (".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        (".rst", "text/prs.fallenstein.rst"),
        (".rtf", "application/rtf"),
        (".tiff", "image/tiff"),
        (".tsv", "text/tab-separated-values"),
        (".txt", "text/plain"),
        (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        (".xml", "text/xml"),
    ]

    for extension, mimetype in expected_mimetypes:
        mimetypes.add_type(mimetype, extension)


_load_mimetypes()


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
