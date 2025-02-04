from __future__ import annotations

import gzip
import io
import mimetypes
import os
import secrets
import shutil
import tempfile
import time
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache, partial
from typing import IO, Any, BinaryIO, Dict, List, Mapping, Optional, Sequence, Tuple, Union, cast
# Add with other imports at top
from unstructured_vlm_partitioner.partition import partition as vlm_partition  # Optional - can also import only when needed

import backoff
import elasticapm
import orjson
import pandas as pd
import requests
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse, StreamingResponse
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError, PdfReadError
from starlette.datastructures import Headers
from starlette.types import Send
from unstructured_prop.ocr.remote_agent import OCR_AGENT_REMOTE

from prepline_general.api import data_storage
from prepline_general.api.api_requests import record_api_request
from prepline_general.api.api_requests.api_quota_check import api_quota_check
from prepline_general.api.filetypes import get_validated_mimetype
from prepline_general.api.logger import logger
from prepline_general.api.metrics import send_partition_metrics
from prepline_general.api.models.form_params import GeneralFormParams
from unstructured.documents.elements import Element
from unstructured.errors import PageCountExceededError
from unstructured.partition.auto import partition
from unstructured.partition.utils.constants import (
    OCR_AGENT_PADDLE,
    OCR_AGENT_TESSERACT,
)
from unstructured.staging.base import (
    convert_to_dataframe,
    convert_to_isd,
    elements_from_json,
)
from unstructured_inference.models.base import UnknownModelException

app = FastAPI()
router = APIRouter()


@lru_cache(maxsize=1)
def _do_not_log_params() -> tuple[str, ...]:
    return (
        ("file",)
        if os.getenv("FREE_TIER_STORAGE_ENABLED", "False") == "True"
        else ("file", "metadata_filename")
    )


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


UNSTRUCTURED_PDF_HI_RES_MAX_PAGES_DEFAULT = 300


@elasticapm.capture_span("pipeline_api")
def pipeline_api(
    file: IO[bytes],
    *,
    request: Request,
    # -- api specific params --
    response_type: str = "application/json",
    coordinates: bool = False,
    org_id: Optional[int] = None,  # Not an api param - just passing through
    # -- chunking options --
    chunking_strategy: Optional[str],
    combine_under_n_chars: Optional[int],
    include_orig_elements: Optional[bool],
    max_characters: int,
    multipage_sections: bool,
    new_after_n_chars: Optional[int],
    overlap: int,
    overlap_all: bool,
    similarity_threshold: Optional[float],
    # --other partition options --
    filename: str = "",
    file_content_type: Optional[str] = None,
    encoding: str = "utf-8",
    hi_res_model_name: Optional[str] = None,
    include_page_breaks: bool = False,
    ocr_languages: Optional[List[str]] = None,
    pdf_infer_table_structure: bool = True,
    skip_infer_table_types: Optional[List[str]] = None,
    strategy: str = "hi_res",
    xml_keep_tags: bool = False,
    languages: Optional[List[str]] = None,
    extract_image_block_types: Optional[List[str]] = None,
    unique_element_ids: Optional[bool] = False,
    starting_page_number: Optional[int] = None,
    include_slide_notes: Optional[bool] = True,
    table_ocr_agent: Optional[str] = OCR_AGENT_TESSERACT,
) -> List[Dict[str, Any]] | str:
    start_process_time = time.time()

    if table_ocr_agent not in (OCR_AGENT_PADDLE, OCR_AGENT_TESSERACT, OCR_AGENT_REMOTE):
        logger.warning(
            "invalide option for table_ocr_agent %s, using %s instead",
            table_ocr_agent,
            OCR_AGENT_TESSERACT,
        )
        table_ocr_agent = OCR_AGENT_TESSERACT

    # FIXME (yao): hack before we refactor open source lib to allow us to pass down a table ocr
    # option
    os.environ["TABLE_OCR_AGENT"] = table_ocr_agent or OCR_AGENT_TESSERACT

    # TODO - belongs in filetype checking logic
    if filename.endswith(".msg"):
        # Note(yuming): convert file type for msg files
        # since fast api might sent the wrong one.
        file_content_type = "application/x-ole-storage"

    if file_content_type == "application/pdf":
        _check_pdf(file)
    pdf_hi_res_max_pages = int(
        os.environ.get(
            "UNSTRUCTURED_PDF_HI_RES_MAX_PAGES",
            UNSTRUCTURED_PDF_HI_RES_MAX_PAGES_DEFAULT,
        ),
    )

    strategy = _validate_strategy(strategy, file_content_type)
    pdf_infer_table_structure = _set_pdf_infer_table_structure(pdf_infer_table_structure, strategy)

    # Parallel mode is set by env variable
    enable_parallel_mode = os.environ.get("UNSTRUCTURED_PARALLEL_MODE_ENABLED", "false")
    pdf_parallel_mode_enabled = enable_parallel_mode == "true"
    if starting_page_number is None:
        starting_page_number = 1

    ocr_languages_str = "+".join(ocr_languages) if ocr_languages and len(ocr_languages) else None

    # Bundle all params to send on to partition
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
        "extract_image_block_types": extract_image_block_types,
        "unique_element_ids": unique_element_ids,
        "starting_page_number": starting_page_number,
        # Inferred from block_types being non-empty
        "extract_image_block_to_payload": bool(extract_image_block_types),
        # -- chunking --
        "chunking_strategy": chunking_strategy,
        "combine_text_under_n_chars": combine_under_n_chars,
        "include_orig_elements": include_orig_elements,
        "multipage_sections": multipage_sections,
        "new_after_n_chars": new_after_n_chars,
        "max_characters": max_characters,
        "overlap": overlap,
        "overlap_all": overlap_all,
        "similarity_threshold": similarity_threshold,
        "pdf_hi_res_max_pages": pdf_hi_res_max_pages,
        "include_slide_notes": include_slide_notes,
        "table_ocr_agent": table_ocr_agent,
    }

    # Add in any api only params (if needed for parallel mode)
    all_kwargs = {
        "coordinates": coordinates,
        **partition_kwargs,
    }

    loggable_params = {k: v for k, v in all_kwargs.items() if k not in _do_not_log_params()}
    logger.info(
        "Attemping to Partition file with filetype %s",
        file_content_type,
        extra={"input_params": loggable_params, "org_id": org_id, "file_type": file_content_type},
    )

    # If file is pdf and parallel mode is on:
    #   split up file and send pages back through api
    #   (send all_kwargs here - we need to pass on api only params)
    #
    # Else:
    #    call partition
    # If file is pdf and parallel mode is on:
#   split up file and send pages back through api
#   (send all_kwargs here - we need to pass on api only params)
#
# Else:
#    call partition
try:
    if strategy == "vlm":
        with elasticapm.capture_span("vlm_partition"):
            from unstructured_vlm_partitioner.partition import partition as vlm_partition
            
            # Create temporary file for VLM processing
            file_extension = file_content_type.split('/')[-1] if file_content_type else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                file.seek(0)  # Ensure we're at start of file
                shutil.copyfileobj(file, temp_file)
                temp_file_path = temp_file.name
            
            try:
                vlm_config = {
                    "api_endpoint": os.getenv("CUSTOMER_VLM_ENDPOINT"),
                    "api_key": os.getenv("CUSTOMER_VLM_API_KEY"),
                }

                elements, _ = vlm_partition(
                    filename=temp_file_path,  # Pass filename instead of file object
                    is_customer_vlm=True,
                    vlm_config=vlm_config,
                    unique_element_ids=unique_element_ids,
                    output_format="application/json"
                )
            finally:
                # Clean up temp file
                os.unlink(temp_file_path)
                
    elif file_content_type == "application/pdf" and pdf_parallel_mode_enabled:
        with elasticapm.capture_span("partition_pdf_splits"):
            pdf = PdfReader(file)
            elements = partition_pdf_splits(
                request=request,
                pdf_pages=pdf.pages,
                **all_kwargs,  # type: ignore[arg-type]
            )
    else:
        with elasticapm.capture_span(
            "partition",
            labels={"strategy": strategy, "chunking_strategy": chunking_strategy or "none"},
        ):
            elements = partition(**partition_kwargs)  # pyright: ignore[reportArgumentType]
        # this may not be accurate since there might be empty pages but this should give us a proxi
        # of how much compute effort is needed
        number_of_pages = elements[-1].metadata.page_number or 1 if elements else 0

        # add metadata to the transaction for the number of pages as well as the
        # strategy. This will help in creating a visualizaton to compare
        # strategies vs the number of pages.
        elasticapm.label(number_of_pages=number_of_pages)
        elasticapm.label(strategy=strategy)

    except OSError as e:
        # OSError isn't caught by our top level handler, so convert it here
        logger.error(e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
    except PageCountExceededError as e:
        raise HTTPException(
            status_code=422,
            detail=f"{e} Check the split_pdf_page functionality of unstructured_client "
            f"to send the file in smaller chunks.",
        )
    except ValueError as e:
        if "Invalid file" in e.args[0]:
            raise HTTPException(
                status_code=400,
                detail=f"{file_content_type} not currently supported",
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
        logger.error(e, exc_info=True)
        raise e
    except UnknownModelException:
        logger.error("Unknown model type: %s", hi_res_model_name)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model type: {hi_res_model_name}",
        )

    process_time_in_seconds = time.time() - start_process_time

    # Send metrics
    try:
        if org_id:
            metrics_kwargs = {
                "encoding": encoding,
                "include_page_breaks": include_page_breaks,
                "model_name": hi_res_model_name,
                "ocr_languages": ocr_languages,
                "pdf_infer_table_structure": pdf_infer_table_structure,
                "skip_infer_table_types": skip_infer_table_types,
                "strategy": strategy,
                "xml_keep_tags": xml_keep_tags,
                "languages": languages,
                "chunking_strategy": chunking_strategy,
                "multipage_sections": multipage_sections,
                "combine_under_n_chars": combine_under_n_chars,
                "new_after_n_chars": new_after_n_chars,
                "max_characters": max_characters,
                "coordinates": coordinates,
            }
            send_partition_metrics(
                org_id,
                file_content_type or "",
                process_time_in_seconds,
                number_of_pages,
                **metrics_kwargs,  # type: ignore
            )
    except Exception as e:
        logger.error("Exception during sending metrics", exc_info=True)
        pass

    # Clean up returned elements
    # Note(austin): pydantic should control this sort of thing for us
    for i, element in enumerate(elements):
        elements[i].metadata.filename = os.path.basename(filename)

        if element.metadata.last_modified:
            elements[i].metadata.last_modified = None

        if element.metadata.file_directory:
            elements[i].metadata.file_directory = None

        if strategy != "od_only":
            if not coordinates and element.metadata.coordinates:
                elements[i].metadata.coordinates = None

            if element.metadata.detection_class_prob:
                elements[i].metadata.detection_class_prob = None

    if response_type == "text/csv":
        df = convert_to_dataframe(elements)
        return df.to_csv(index=False)

    result = convert_to_isd(elements)

    return result


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


def _validate_strategy(strategy: str, file_content_type: Optional[str]) -> str:
    strategy = strategy.lower()
    strategies = ["fast", "hi_res", "auto", "ocr_only", "od_only", "vlm"]  # Add vlm here
    if strategy not in strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy: {strategy}. Must be one of {strategies}",
        )

    # Add VLM validation
    if strategy == "vlm":
        if not os.getenv("CUSTOMER_VLM_ENDPOINT"):
            raise HTTPException(
                status_code=400,
                detail="VLM strategy requires CUSTOMER_VLM_ENDPOINT environment variable"
            )
        if not os.getenv("CUSTOMER_VLM_API_KEY"):
            raise HTTPException(
                status_code=400,
                detail="VLM strategy requires CUSTOMER_VLM_API_KEY environment variable"
            )
    if (
        strategy == "od_only"
        and file_content_type
        and file_content_type != "application/pdf"
        and "image" not in file_content_type
    ):
        raise HTTPException(
            status_code=400,
            detail="'od_only' strategy is only available for PDF and image files",
        )
    return strategy


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
            },
        )
        async for chunk in self.body_iterator:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)  # type: ignore
                chunk = b64encode(chunk)
            await send(
                {"type": "http.response.body", "body": self.build_part(chunk), "more_body": True},
            )

        await send({"type": "http.response.body", "body": b"", "more_body": False})


def ungz_file(file: UploadFile, gz_uncompressed_content_type: Optional[str] = None) -> UploadFile:
    filename = str(file.filename) if file.filename else ""
    if filename.endswith(".gz"):
        filename = filename[:-3]

    if not gz_uncompressed_content_type:
        gz_uncompressed_content_type = str(mimetypes.guess_type(filename)[0])

    output_file = tempfile.SpooledTemporaryFile()
    with gzip.open(file.file) as gzfile:
        shutil.copyfileobj(gzfile, output_file, length=1024 * 1024)  # type: ignore
    output_file.seek(0)

    return UploadFile(
        file=cast(BinaryIO, output_file),
        size=os.fstat(output_file.fileno()).st_size,
        filename=filename,
        headers=Headers({"content-type": gz_uncompressed_content_type}),
    )


@router.get("/general/v0/general", include_in_schema=False)
@router.get("/general/v1.0.58/general", include_in_schema=False)
async def handle_invalid_get_request():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Only POST requests are supported.",
    )


@elasticapm.capture_span()
@router.post(
    "/general/v0/general",
    openapi_extra={"x-speakeasy-name-override": "partition"},
    tags=["general"],
    summary="Summary",
    description="Description",
    operation_id="partition",
)
@router.post("/general/v1.0.58/general", include_in_schema=False)
def general_partition(
    background_tasks: BackgroundTasks,
    request: Request,
    files: List[UploadFile],
    unstructured_api_key: Union[str, None] = Header(default=None),
    # cannot use annotated type here because of a bug described here:
    # https://github.com/tiangolo/fastapi/discussions/10280
    # The openapi metadata must be added separately in openapi.py file.
    # TODO: Check if the bug is fixed and change the declaration to use
    #     Annoteted[List[UploadFile], File(...)]
    # For new parameters - add them in models/form_params.py
    form_params: GeneralFormParams = Depends(GeneralFormParams.as_form),
):
    # -- must have a valid API key --
    if api_key_env := os.environ.get("UNSTRUCTURED_API_KEY"):
        api_key = request.headers.get("unstructured-api-key")
        if api_key != api_key_env:
            raise HTTPException(
                detail=f"API key {api_key} is invalid",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

    accept_type = request.headers.get("Accept")

    # -- detect response content-type conflict when multiple files are uploaded --
    if (
        len(files) > 1
        and accept_type
        and accept_type
        not in [
            "*/*",
            "multipart/mixed",
            "application/json",
            "text/csv",
        ]
    ):
        raise HTTPException(
            detail=f"Conflict in media type {accept_type} with response type 'multipart/mixed'.\n",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )

    # -- unzip any uploaded files that need it --
    for idx, file in enumerate(files):
        is_content_type_gz = file.content_type == "application/gzip"
        is_extension_gz = file.filename and file.filename.endswith(".gz")
        if is_content_type_gz or is_extension_gz:
            files[idx] = ungz_file(file, form_params.gz_uncompressed_content_type)

    request.state.__dict__["bookkeeper"] = record_api_request.FileAccountingObj()
    passed_quota_check, api_quota_check_info_dict = api_quota_check(request)
    background_tasks.add_task(
        record_api_request.send_api_request_info,
        datetime.utcnow(),
        passed_quota_check,
        api_quota_check_info_dict,
        request,
    )

    def response_generator(is_multipart: bool):
        for file in files:
            file_content_type = get_validated_mimetype(
                file,
                content_type_hint=form_params.content_type,
            )

            _file = file.file
            org_id = api_quota_check_info_dict["org_id"] if api_quota_check_info_dict else None
            pipeline_api_kwargs: dict[str, Any] = {
                "request": request,
                "org_id": org_id,
                "filename": file.filename,
                "file_content_type": file_content_type,
                "response_type": form_params.output_format,
                "coordinates": form_params.coordinates,
                "encoding": form_params.encoding,
                "extract_image_block_types": form_params.extract_image_block_types,
                "hi_res_model_name": form_params.hi_res_model_name,
                "include_page_breaks": form_params.include_page_breaks,
                "ocr_languages": form_params.ocr_languages,
                "pdf_infer_table_structure": form_params.pdf_infer_table_structure,
                "skip_infer_table_types": form_params.skip_infer_table_types,
                "strategy": form_params.strategy,
                "xml_keep_tags": form_params.xml_keep_tags,
                "languages": form_params.languages,
                "unique_element_ids": form_params.unique_element_ids,
                "starting_page_number": form_params.starting_page_number,
                # -- chunking options --
                "chunking_strategy": form_params.chunking_strategy,
                "combine_under_n_chars": form_params.combine_under_n_chars,
                "include_orig_elements": form_params.include_orig_elements,
                "max_characters": form_params.max_characters,
                "multipage_sections": form_params.multipage_sections,
                "new_after_n_chars": form_params.new_after_n_chars,
                "overlap": form_params.overlap,
                "overlap_all": form_params.overlap_all,
                "similarity_threshold": form_params.similarity_threshold,
                "include_slide_notes": form_params.include_slide_notes,
                "table_ocr_agent": form_params.table_ocr_agent,
            }

            with data_storage.ApiDataStorage(
                _file,
                api_quota_check_info_dict,
                pipeline_api_kwargs,
            ) as file_storage:
                response = pipeline_api(
                    _file,
                    **pipeline_api_kwargs,  # pyright: ignore[reportArgumentType]
                )
                bookkeeper: record_api_request.FileAccountingObj = request.state.bookkeeper

                if isinstance(response, List):
                    bookkeeper.num_of_pages = record_api_request.get_num_of_pages_from_elements(
                        response,
                        org_id,
                    )

                record_api_request.update_api_request_info(
                    bookkeeper,
                    _file,
                    **pipeline_api_kwargs,
                )
                file_storage.save(response, status.HTTP_200_OK, "success")  # type: ignore

            yield (
                orjson.dumps(response).decode("utf-8")
                if is_multipart and type(response) not in [str, bytes]
                else (
                    PlainTextResponse(response, headers={"content-type": "text/csv; charset=utf-8"})
                    if not is_multipart and form_params.output_format == "text/csv"
                    else response
                )
            )

    def join_responses(
        responses: Sequence[str | List[Dict[str, Any]] | PlainTextResponse],
    ) -> List[str | List[Dict[str, Any]]] | PlainTextResponse:
        if form_params.output_format != "text/csv":
            return cast(List[Union[str, List[Dict[str, Any]]]], responses)
        responses = cast(List[PlainTextResponse], responses)
        data: pd.DataFrame = pd.read_csv(  # pyright: ignore[reportUnknownMemberType]
            io.BytesIO(responses[0].body),
        )
        if len(responses) > 1:
            for resp in responses[1:]:
                resp_data = pd.read_csv(  # pyright: ignore[reportUnknownMemberType]
                    io.BytesIO(resp.body),
                )
                data = data.merge(  # pyright: ignore[reportUnknownMemberType]
                    resp_data,
                    how="outer",
                )
        resp = PlainTextResponse(data.to_csv(index=False))
        resp.headers["content-type"] = "text/csv; charset=utf-8"
        return resp

    return (
        MultipartMixedResponse(
            response_generator(is_multipart=True),
            content_type=form_params.output_format,
        )
        if accept_type == "multipart/mixed"
        else (
            list(response_generator(is_multipart=False))[0]
            if len(files) == 1
            else join_responses(list(response_generator(is_multipart=False)))
        )
    )


app.include_router(router)
