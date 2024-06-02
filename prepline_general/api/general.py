from __future__ import annotations

import gzip
import io
import json
import logging
import mimetypes
import os
import secrets
import zipfile
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import IO, Any, Dict, List, Mapping, Optional, Sequence, Tuple

import backoff
import psutil
import requests
from fastapi import (
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pypdf import PdfReader, PageObject, PdfWriter
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import Send
from unstructured.documents.elements import Element
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_from_json, convert_to_dataframe, convert_to_isd
from unstructured_inference.models.base import UnknownModelException
from unstructured_inference.models.chipper import MODEL_TYPES as CHIPPER_MODEL_TYPES

from prepline_general.api.memory_protection import ChipperMemoryProtection
from prepline_general.api.validation import (
    _check_pdf,
    _validate_hi_res_model_name,
    _validate_strategy,
)

logger = logging.getLogger("unstructured_api")

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


def get_pdf_splits(pdf_pages: Sequence[PageObject], split_size: int = 1):
    """Given a pdf (PdfReader) with n pages, split it into pdfs each with split_size # of pages.

    Return the files with their page offset in the form [(BytesIO, int)]
    """
    offset = 0

    while offset < len(pdf_pages):
        new_pdf = PdfWriter()
        pdf_buffer = io.BytesIO()

        end = offset + split_size
        for page in pdf_pages[offset:end]:
            new_pdf.add_page(page)

        new_pdf.write(pdf_buffer)
        pdf_buffer.seek(0)

        yield (pdf_buffer.read(), offset)
        offset += split_size


# Do not retry with these status codes
def is_non_retryable(e: Exception) -> bool:
    # -- `Exception` doesn't have a `.status_code` attribute so the check of status-code would
    # -- itself raise `AttributeError` when e is say ValueError or TypeError, etc.
    if not isinstance(e, HTTPException):
        return True
    return 400 <= e.status_code < 500


@backoff.on_exception(
    backoff.expo,
    HTTPException,
    max_tries=int(os.environ.get("UNSTRUCTURED_PARALLEL_RETRY_ATTEMPTS", 2)) + 1,
    giveup=is_non_retryable,
    logger=logger,
)
def call_api(
    request_url: str,
    api_key: str,
    filename: str,
    file: IO[bytes],
    content_type: str,
    **partition_kwargs: Any,
) -> str:
    """Call the api with the given request_url."""
    headers = {"unstructured-api-key": api_key}

    response = requests.post(
        request_url,
        files={"files": (filename, file, content_type)},
        data=partition_kwargs,
        headers=headers,
    )

    if response.status_code != 200:
        detail = response.json().get("detail") or response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    return response.text


def partition_file_via_api(
    file_tuple: Tuple[IO[bytes], int],
    request: Request,
    filename: str,
    content_type: str,
    **partition_kwargs: Any,
) -> List[Element]:
    """Send the given file to be partitioned remotely with retry logic.

    The remote url is set by the `UNSTRUCTURED_PARALLEL_MODE_URL` environment variable.

    Args:
    `file_tuple` is a file-like object and byte offset of a page (file, page_offest)
    `request` is used to forward the api key header
    `filename` and `content_type` are passed in the file form data
    `partition_kwargs` holds any form parameters to be sent on
    """
    file, page_offset = file_tuple

    request_url = os.environ.get("UNSTRUCTURED_PARALLEL_MODE_URL")
    if not request_url:
        raise HTTPException(status_code=500, detail="Parallel mode enabled but no url set!")

    api_key = request.headers.get("unstructured-api-key", default="")
    partition_kwargs["starting_page_number"] = (
        partition_kwargs.get("starting_page_number", 1) + page_offset
    )

    result = call_api(
        request_url,
        api_key,
        filename,
        file,
        content_type,
        **partition_kwargs,
    )
    return elements_from_json(text=result)


def partition_pdf_splits(
    request: Request,
    pdf_pages: Sequence[PageObject],
    file: IO[bytes],
    metadata_filename: str,
    content_type: str,
    coordinates: bool,
    **partition_kwargs: Any,
) -> List[Element]:
    """Split a pdf into chunks and process in parallel with more api calls.

    Or partition locally if the chunk is small enough. As soon as any remote call fails, bubble up
    the error.

    Arguments:
    request is used to forward relevant headers to the api calls
    file, metadata_filename and content_type are passed on in the file argument to requests.post
    coordinates is passed on to the api calls, but cannot be used in the local partition case
    partition_kwargs holds any others parameters that will be forwarded, or passed to partition
    """
    pages_per_pdf = int(os.environ.get("UNSTRUCTURED_PARALLEL_MODE_SPLIT_SIZE", 1))

    # If it's small enough, just process locally
    if len(pdf_pages) <= pages_per_pdf:
        return partition(
            file=file,
            metadata_filename=metadata_filename,
            content_type=content_type,
            **partition_kwargs,
        )

    results: List[Element] = []
    page_iterator = get_pdf_splits(pdf_pages, split_size=pages_per_pdf)

    partition_func = partial(
        partition_file_via_api,
        request=request,
        filename=metadata_filename,
        content_type=content_type,
        coordinates=coordinates,
        **partition_kwargs,
    )

    thread_count = int(os.environ.get("UNSTRUCTURED_PARALLEL_MODE_THREADS", 3))
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        for result in executor.map(partition_func, page_iterator):
            results.extend(result)

    return results


def pipeline_api(
    file: IO[bytes],
    request: Request,
    # -- chunking options --
    chunking_strategy: Optional[str],
    combine_under_n_chars: Optional[int],
    max_characters: int,
    multipage_sections: bool,
    new_after_n_chars: Optional[int],
    overlap: int,
    overlap_all: bool,
    # ----------------------
    filename: str = "",
    file_content_type: Optional[str] = None,
    response_type: str = "application/json",
    coordinates: bool = False,
    encoding: str = "utf-8",
    hi_res_model_name: Optional[str] = None,
    include_page_breaks: bool = False,
    ocr_languages: Optional[List[str]] = None,
    pdf_infer_table_structure: bool = True,
    skip_infer_table_types: Optional[List[str]] = None,
    strategy: str = "auto",
    xml_keep_tags: bool = False,
    languages: Optional[List[str]] = None,
    extract_image_block_types: Optional[List[str]] = None,
    unique_element_ids: Optional[bool] = False,
    starting_page_number: Optional[int] = None,
) -> List[Dict[str, Any]] | str:
    if filename.endswith(".msg"):
        # Note(yuming): convert file type for msg files
        # since fast api might sent the wrong one.
        file_content_type = "application/x-ole-storage"

    # We don't want to keep logging the same params for every parallel call
    is_internal_request = (
        (
            request.headers.get("X-Forwarded-For")
            and str(request.headers.get("X-Forwarded-For")).startswith("10.")
        )
        # -- NOTE(scanny): request.client is None in certain testing environments --
        or (request.client and request.client.host.startswith("10."))
    )

    if not is_internal_request:
        logger.debug(
            "pipeline_api input params: {}".format(
                json.dumps(
                    {
                        "filename": filename,
                        "response_type": response_type,
                        "coordinates": coordinates,
                        "encoding": encoding,
                        "hi_res_model_name": hi_res_model_name,
                        "include_page_breaks": include_page_breaks,
                        "ocr_languages": ocr_languages,
                        "pdf_infer_table_structure": pdf_infer_table_structure,
                        "skip_infer_table_types": skip_infer_table_types,
                        "strategy": strategy,
                        "xml_keep_tags": xml_keep_tags,
                        "languages": languages,
                        "extract_image_block_types": extract_image_block_types,
                        "unique_element_ids": unique_element_ids,
                        "chunking_strategy": chunking_strategy,
                        "combine_under_n_chars": combine_under_n_chars,
                        "max_characters": max_characters,
                        "multipage_sections": multipage_sections,
                        "new_after_n_chars": new_after_n_chars,
                        "overlap": overlap,
                        "overlap_all": overlap_all,
                        "starting_page_number": starting_page_number,
                    },
                    default=str,
                )
            )
        )

        logger.debug(f"filetype: {file_content_type}")

    _check_free_memory()

    if file_content_type == "application/pdf":
        _check_pdf(file)

    hi_res_model_name = _validate_hi_res_model_name(hi_res_model_name, coordinates)
    strategy = _validate_strategy(strategy)
    pdf_infer_table_structure = _set_pdf_infer_table_structure(pdf_infer_table_structure, strategy)

    # Parallel mode is set by env variable
    enable_parallel_mode = os.environ.get("UNSTRUCTURED_PARALLEL_MODE_ENABLED", "false")
    pdf_parallel_mode_enabled = enable_parallel_mode == "true"
    if starting_page_number is None:
        starting_page_number = 1

    ocr_languages_str = "+".join(ocr_languages) if ocr_languages and len(ocr_languages) else None

    extract_image_block_to_payload = bool(extract_image_block_types)

    try:
        logger.debug(
            "partition input data: {}".format(
                json.dumps(
                    {
                        "content_type": file_content_type,
                        "strategy": strategy,
                        "ocr_languages": ocr_languages_str,
                        "coordinates": coordinates,
                        "pdf_infer_table_structure": pdf_infer_table_structure,
                        "include_page_breaks": include_page_breaks,
                        "encoding": encoding,
                        "hi_res_model_name": hi_res_model_name,
                        "xml_keep_tags": xml_keep_tags,
                        "skip_infer_table_types": skip_infer_table_types,
                        "languages": languages,
                        "chunking_strategy": chunking_strategy,
                        "multipage_sections": multipage_sections,
                        "combine_under_n_chars": combine_under_n_chars,
                        "new_after_n_chars": new_after_n_chars,
                        "max_characters": max_characters,
                        "overlap": overlap,
                        "overlap_all": overlap_all,
                        "extract_image_block_types": extract_image_block_types,
                        "extract_image_block_to_payload": extract_image_block_to_payload,
                        "unique_element_ids": unique_element_ids,
                    },
                    default=str,
                )
            )
        )

        partition_kwargs = {
            "file": file,
            "metadata_filename": filename,
            "content_type": file_content_type,
            "encoding": encoding,
            "include_page_breaks": include_page_breaks,
            "hi_res_model_name": hi_res_model_name,
            "ocr_languages": ocr_languages_str,
            "pdf_infer_table_structure": pdf_infer_table_structure,
            "skip_infer_table_types": skip_infer_table_types,
            "strategy": strategy,
            "xml_keep_tags": xml_keep_tags,
            "languages": languages,
            "chunking_strategy": chunking_strategy,
            "multipage_sections": multipage_sections,
            "combine_text_under_n_chars": combine_under_n_chars,
            "new_after_n_chars": new_after_n_chars,
            "max_characters": max_characters,
            "overlap": overlap,
            "overlap_all": overlap_all,
            "extract_image_block_types": extract_image_block_types,
            "extract_image_block_to_payload": extract_image_block_to_payload,
            "unique_element_ids": unique_element_ids,
            "starting_page_number": starting_page_number,
        }

        if file_content_type == "application/pdf" and pdf_parallel_mode_enabled:
            pdf = PdfReader(file)
            elements = partition_pdf_splits(
                request=request,
                pdf_pages=pdf.pages,
                coordinates=coordinates,
                **partition_kwargs,  # type: ignore # pyright: ignore[reportGeneralTypeIssues]
            )
        elif hi_res_model_name and hi_res_model_name in CHIPPER_MODEL_TYPES:
            with ChipperMemoryProtection():
                elements = partition(**partition_kwargs)  # pyright: ignore[reportGeneralTypeIssues]
        else:
            elements = partition(**partition_kwargs)  # pyright: ignore[reportGeneralTypeIssues]

    except OSError as e:
        if isinstance(e.args[0], str) and (
            "chipper-fast-fine-tuning is not a local folder" in e.args[0]
            or "ved-fine-tuning is not a local folder" in e.args[0]
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "The Chipper model is not available for download. It can be accessed via the"
                    " official hosted API."
                ),
            )

        # OSError isn't caught by our top level handler, so convert it here
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    except ValueError as e:
        if "Invalid file" in e.args[0]:
            raise HTTPException(
                status_code=400, detail=f"{file_content_type} not currently supported"
            )
        if "Unstructured schema" in e.args[0]:
            raise HTTPException(
                status_code=400,
                detail="Json schema does not match the Unstructured schema",
            )
        if "fast strategy is not available for image files" in e.args[0]:
            raise HTTPException(
                status_code=400,
                detail="The fast strategy is not available for image files",
            )

        raise e
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=422,
            detail="File is not a valid docx",
        )

    except UnknownModelException:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model type: {hi_res_model_name}",
        )

    # Clean up returned elements
    # Note(austin): pydantic should control this sort of thing for us
    for i, element in enumerate(elements):
        elements[i].metadata.filename = os.path.basename(filename)

        if not coordinates and element.metadata.coordinates:
            elements[i].metadata.coordinates = None

        if element.metadata.last_modified:
            elements[i].metadata.last_modified = None

        if element.metadata.file_directory:
            elements[i].metadata.file_directory = None

        if element.metadata.detection_class_prob:
            elements[i].metadata.detection_class_prob = None

    if response_type == "text/csv":
        df = convert_to_dataframe(elements)
        return df.to_csv(index=False)

    result = convert_to_isd(elements)

    return result


def _check_free_memory():
    """Reject traffic when free memory is below minimum (default 2GB)."""
    mem = psutil.virtual_memory()
    memory_free_minimum = int(os.environ.get("UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB", 2048))

    if mem.available <= memory_free_minimum * 1024 * 1024:
        logger.warning(f"Rejecting because free memory is below {memory_free_minimum} MB")
        raise HTTPException(
            status_code=503, detail="Server is under heavy load. Please try again later."
        )


def _set_pdf_infer_table_structure(pdf_infer_table_structure: bool, strategy: str) -> bool:
    """Avoids table inference in "fast" and "ocr_only" runs."""
    return strategy in ("hi_res", "auto") and pdf_infer_table_structure


class MultipartMixedResponse(StreamingResponse):
    CRLF = b"\r\n"

    def __init__(self, *args: Any, content_type: Optional[str] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.content_type = content_type

    def init_headers(self, headers: Optional[Mapping[str, str]] = None) -> None:
        super().init_headers(headers)
        self.boundary_value = secrets.token_hex(16)
        content_type = f'multipart/mixed; boundary="{self.boundary_value}"'
        self.raw_headers.append((b"content-type", content_type.encode("latin-1")))

    @property
    def boundary(self):
        return b"--" + self.boundary_value.encode()

    def _build_part_headers(self, headers: Dict[str, Any]) -> bytes:
        header_bytes = b""
        for header, value in headers.items():
            header_bytes += f"{header}: {value}".encode() + self.CRLF
        return header_bytes

    def build_part(self, chunk: bytes) -> bytes:
        part = self.boundary + self.CRLF
        part_headers = {"Content-Length": len(chunk), "Content-Transfer-Encoding": "base64"}
        if self.content_type is not None:
            part_headers["Content-Type"] = self.content_type
        part += self._build_part_headers(part_headers)
        part += self.CRLF + chunk + self.CRLF
        return part

    async def stream_response(self, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)
                chunk = b64encode(chunk)
            await send(
                {"type": "http.response.body", "body": self.build_part(chunk), "more_body": True}
            )

        await send({"type": "http.response.body", "body": b"", "more_body": False})


def ungz_file(file: UploadFile, gz_uncompressed_content_type: Optional[str] = None) -> UploadFile:
    def return_content_type(filename: str):
        if gz_uncompressed_content_type:
            return gz_uncompressed_content_type
        else:
            return str(mimetypes.guess_type(filename)[0])

    filename = str(file.filename) if file.filename else ""
    if filename.endswith(".gz"):
        filename = filename[:-3]

    gzip_file = gzip.open(file.file).read()
    return UploadFile(
        file=io.BytesIO(gzip_file),
        size=len(gzip_file),
        filename=filename,
        headers=Headers({"content-type": return_content_type(filename)}),
    )
