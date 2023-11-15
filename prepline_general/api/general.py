# Standard Library Imports
import io
import os
import gzip
import mimetypes
from typing import List, Union, Optional, Mapping
from base64 import b64encode
from typing import Optional
from functools import partial
import json
import logging
import zipfile

# External Package Imports
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from base64 import b64encode
from typing import Optional, Mapping
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import pypdf
from pypdf import PdfReader, PdfWriter
import psutil
import requests
import backoff
from typing import Optional, Mapping
from fastapi import (
    status,
    FastAPI,
    File,
    Form,
    Request,
    UploadFile,
    APIRouter,
    HTTPException,
)
from fastapi.responses import PlainTextResponse, StreamingResponse
from starlette.datastructures import Headers
from starlette.types import Send
import secrets

# Unstructured Imports
from unstructured.partition.auto import partition
from unstructured.staging.base import (
    convert_to_isd,
    convert_to_dataframe,
    elements_from_json,
)
from unstructured_inference.models.chipper import MODEL_TYPES as CHIPPER_MODEL_TYPES


app = FastAPI()
router = APIRouter()


def is_expected_response_type(media_type, response_type):
    if media_type == "application/json" and response_type not in [dict, list]:
        return True
    elif media_type == "text/csv" and response_type != str:
        return True
    else:
        return False


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
)

if not os.environ.get("UNSTRUCTURED_ALLOWED_MIMETYPES", None):
    os.environ["UNSTRUCTURED_ALLOWED_MIMETYPES"] = DEFAULT_MIMETYPES


def get_pdf_splits(pdf_pages, split_size=1):
    """
    Given a pdf (PdfReader) with n pages, split it into pdfs each with split_size # of pages
    Return the files with their page offset in the form [( BytesIO, int)]
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
def is_non_retryable(e):
    return 400 <= e.status_code < 500


@backoff.on_exception(
    backoff.expo,
    HTTPException,
    max_tries=int(os.environ.get("UNSTRUCTURED_PARALLEL_RETRY_ATTEMPTS", 2)) + 1,
    giveup=is_non_retryable,
    logger=logger,
)
def call_api(request_url, api_key, filename, file, content_type, **partition_kwargs):
    """
    Call the api with the given request_url.
    """
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


def partition_file_via_api(file_tuple, request, filename, content_type, **partition_kwargs):
    """
    Send the given file to be partitioned remotely with retry logic,
    where the remote url is set by env var.

    Args:
    file_tuple is in the form (file, page_offest)
    request is used to forward the api key header
    filename and content_type are passed in the file form data
    partition_kwargs holds any form parameters to be sent on
    """
    file, page_offset = file_tuple

    request_url = os.environ.get("UNSTRUCTURED_PARALLEL_MODE_URL")
    if not request_url:
        raise HTTPException(status_code=500, detail="Parallel mode enabled but no url set!")

    api_key = request.headers.get("unstructured-api-key")

    result = call_api(request_url, api_key, filename, file, content_type, **partition_kwargs)
    elements = elements_from_json(text=result)

    # We need to account for the original page numbers
    for element in elements:
        if element.metadata.page_number:
            # Page number could be None if we include page breaks
            element.metadata.page_number += page_offset

    return elements


def partition_pdf_splits(
    request, pdf_pages, file, metadata_filename, content_type, coordinates, **partition_kwargs
):
    """
    Split a pdf into chunks and process in parallel with more api calls, or partition
    locally if the chunk is small enough. As soon as any remote call fails, bubble up
    the error.

    Arguments:
    request is used to forward relevant headers to the api calls
    file, metadata_filename and content_type are passed on in the file argument to requests.post
    coordinates is passed on to the api calls, but cannot be used in the local partition case
    partition_kwargs holds any others parameters that will be forwarded, or passed to partition
    """
    pages_per_pdf = int(os.environ.get("UNSTRUCTURED_PARALLEL_MODE_SPLIT_SIZE", 1))

    # If it's small enough, just process locally
    # (Some kwargs need to be renamed for local partition)
    if len(pdf_pages) <= pages_per_pdf:
        if partition_kwargs.get("hi_res_model_name"):
            partition_kwargs["model_name"] = partition_kwargs.pop("hi_res_model_name")

        return partition(
            file=file,
            metadata_filename=metadata_filename,
            content_type=content_type,
            **partition_kwargs,
        )

    results = []
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


IS_CHIPPER_PROCESSING = False


class ChipperMemoryProtection:
    """
    Chipper calls are expensive, and right now we can only do one call at a time.
    If the model is in use, return a 503 error. The API should scale up and the user can try again
    on a different server.
    """

    def __enter__(self):
        global IS_CHIPPER_PROCESSING
        if IS_CHIPPER_PROCESSING:
            # Log here so we can track how often it happens
            logger.error("Chipper is already is use")
            raise HTTPException(
                status_code=503, detail="Server is under heavy load. Please try again later."
            )

        IS_CHIPPER_PROCESSING = True

    def __exit__(self, exc_type, exc_value, exc_tb):
        global IS_CHIPPER_PROCESSING
        IS_CHIPPER_PROCESSING = False


def pipeline_api(
    file,
    request=None,
    filename="",
    file_content_type=None,
    response_type="application/json",
    m_coordinates=[],
    m_encoding=[],
    m_hi_res_model_name=[],
    m_include_page_breaks=[],
    m_ocr_languages=None,
    m_pdf_infer_table_structure=[],
    m_skip_infer_table_types=[],
    m_strategy=[],
    m_xml_keep_tags=[],
    languages=None,
    m_chunking_strategy=[],
    m_multipage_sections=[],
    m_combine_under_n_chars=[],
    m_new_after_n_chars=[],
    m_max_characters=[],
):
    if filename.endswith(".msg"):
        # Note(yuming): convert file type for msg files
        # since fast api might sent the wrong one.
        file_content_type = "application/x-ole-storage"

    # We don't want to keep logging the same params for every parallel call
    origin_ip = request.headers.get("X-Forwarded-For") or request.client.host
    is_internal_request = origin_ip.startswith("10.")

    if not is_internal_request:
        logger.debug(
            "pipeline_api input params: {}".format(
                json.dumps(
                    {
                        "filename": filename,
                        "response_type": response_type,
                        "m_coordinates": m_coordinates,
                        "m_encoding": m_encoding,
                        "m_hi_res_model_name": m_hi_res_model_name,
                        "m_include_page_breaks": m_include_page_breaks,
                        "m_ocr_languages": m_ocr_languages,
                        "m_pdf_infer_table_structure": m_pdf_infer_table_structure,
                        "m_skip_infer_table_types": m_skip_infer_table_types,
                        "m_strategy": m_strategy,
                        "m_xml_keep_tags": m_xml_keep_tags,
                        "languages": languages,
                        "m_chunking_strategy": m_chunking_strategy,
                        "m_multipage_sections": m_multipage_sections,
                        "m_combine_under_n_chars": m_combine_under_n_chars,
                        "new_after_n_chars": m_new_after_n_chars,
                        "m_max_characters": m_max_characters,
                    },
                    default=str,
                )
            )
        )

        logger.debug(f"filetype: {file_content_type}")

    # Reject traffic when free memory is below minimum
    # Default to 2GB
    mem = psutil.virtual_memory()
    memory_free_minimum = int(os.environ.get("UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB", 2048))

    if mem.available <= memory_free_minimum * 1024 * 1024:
        raise HTTPException(
            status_code=503, detail="Server is under heavy load. Please try again later."
        )

    if file_content_type == "application/pdf":
        try:
            pdf = PdfReader(file)

            # This will raise if the file is encrypted
            pdf.metadata
        except pypdf.errors.FileNotDecryptedError:
            raise HTTPException(
                status_code=400,
                detail="File is encrypted. Please decrypt it with password.",
            )
        except pypdf.errors.PdfReadError:
            raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")

    strategy = (m_strategy[0] if len(m_strategy) else "auto").lower()
    strategies = ["fast", "hi_res", "auto", "ocr_only"]
    if strategy not in strategies:
        raise HTTPException(
            status_code=400, detail=f"Invalid strategy: {strategy}. Must be one of {strategies}"
        )

    show_coordinates_str = (m_coordinates[0] if len(m_coordinates) else "false").lower()
    show_coordinates = show_coordinates_str == "true"

    hi_res_model_name = m_hi_res_model_name[0] if len(m_hi_res_model_name) else None

    # Make sure chipper aliases to the latest model
    if hi_res_model_name and hi_res_model_name == "chipper":
        hi_res_model_name = "chipperv2"

    if hi_res_model_name and hi_res_model_name in CHIPPER_MODEL_TYPES and show_coordinates:
        raise HTTPException(
            status_code=400,
            detail=f"coordinates aren't available when using the {hi_res_model_name} model type",
        )

    # Parallel mode is set by env variable
    enable_parallel_mode = os.environ.get("UNSTRUCTURED_PARALLEL_MODE_ENABLED", "false")
    pdf_parallel_mode_enabled = enable_parallel_mode == "true"

    ocr_languages = "+".join(m_ocr_languages) if m_ocr_languages and len(m_ocr_languages) else None

    include_page_breaks_str = (
        m_include_page_breaks[0] if len(m_include_page_breaks) else "false"
    ).lower()
    include_page_breaks = include_page_breaks_str == "true"

    encoding = m_encoding[0] if len(m_encoding) else None

    xml_keep_tags_str = (m_xml_keep_tags[0] if len(m_xml_keep_tags) else "false").lower()
    xml_keep_tags = xml_keep_tags_str == "true"

    pdf_infer_table_structure = (
        m_pdf_infer_table_structure[0] if len(m_pdf_infer_table_structure) else "false"
    ).lower()
    if strategy == "hi_res" and pdf_infer_table_structure == "true":
        pdf_infer_table_structure = True
    else:
        pdf_infer_table_structure = False

    skip_infer_table_types = (
        m_skip_infer_table_types[0] if len(m_skip_infer_table_types) else ["pdf", "jpg", "png"]
    )

    chunking_strategy = m_chunking_strategy[0].lower() if len(m_chunking_strategy) else None
    chunk_strategies = ["by_title"]
    if chunking_strategy and (chunking_strategy not in chunk_strategies):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chunking strategy: {chunking_strategy}. Must be one of {chunk_strategies}",
        )

    multipage_sections_str = (
        m_multipage_sections[0] if len(m_multipage_sections) else "true"
    ).lower()
    multipage_sections = multipage_sections_str == "true"

    combine_under_n_chars = (
        int(m_combine_under_n_chars[0])
        if m_combine_under_n_chars and m_combine_under_n_chars[0].isdigit()
        else 500
    )

    new_after_n_chars = (
        int(m_new_after_n_chars[0])
        if m_new_after_n_chars and m_new_after_n_chars[0].isdigit()
        else 1500
    )

    max_characters = (
        int(m_max_characters[0]) if m_max_characters and m_max_characters[0].isdigit() else 1500
    )

    try:
        logger.debug(
            "partition input data: {}".format(
                json.dumps(
                    {
                        "content_type": file_content_type,
                        "strategy": strategy,
                        "ocr_languages": ocr_languages,
                        "coordinates": show_coordinates,
                        "pdf_infer_table_structure": pdf_infer_table_structure,
                        "include_page_breaks": include_page_breaks,
                        "encoding": encoding,
                        "model_name": hi_res_model_name,
                        "xml_keep_tags": xml_keep_tags,
                        "skip_infer_table_types": skip_infer_table_types,
                        "languages": languages,
                        "chunking_strategy": chunking_strategy,
                        "multipage_sections": multipage_sections,
                        "combine_under_n_chars": combine_under_n_chars,
                        "new_after_n_chars": new_after_n_chars,
                        "max_characters": max_characters,
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
        }

        if file_content_type == "application/pdf" and pdf_parallel_mode_enabled:
            # Be careful of naming differences in api params vs partition params!
            # These kwargs are going back into the api, not into partition
            # They need to be switched back in partition_pdf_splits
            if partition_kwargs.get("model_name"):
                partition_kwargs["hi_res_model_name"] = partition_kwargs.pop("model_name")

            elements = partition_pdf_splits(
                request=request,
                pdf_pages=pdf.pages,
                coordinates=show_coordinates,
                **partition_kwargs,
            )
        elif hi_res_model_name and hi_res_model_name in CHIPPER_MODEL_TYPES:
            with ChipperMemoryProtection():
                elements = partition(**partition_kwargs)
        else:
            elements = partition(**partition_kwargs)

    except OSError as e:
        if (
            "chipper-fast-fine-tuning is not a local folder" in e.args[0]
            or "ved-fine-tuning is not a local folder" in e.args[0]
        ):
            raise HTTPException(
                status_code=400,
                detail="The Chipper model is not available for download. It can be accessed via the official hosted API.",
            )

        raise e
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

        raise e
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="File is not a valid docx",
        )

    # Clean up returned elements
    # Note(austin): pydantic should control this sort of thing for us
    for i, element in enumerate(elements):
        elements[i].metadata.filename = os.path.basename(filename)

        if not show_coordinates and element.metadata.coordinates:
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


def get_validated_mimetype(file):
    """
    Return a file's mimetype, either via the file.content_type or the mimetypes lib if that's too
    generic. If the user has set UNSTRUCTURED_ALLOWED_MIMETYPES, validate against this list and
    return HTTP 400 for an invalid type.
    """
    content_type = file.content_type
    if not content_type or content_type == "application/octet-stream":
        content_type = mimetypes.guess_type(str(file.filename))[0]

        # Some filetypes missing for this library, just hardcode them for now
        if not content_type:
            if file.filename.endswith(".md"):
                content_type = "text/markdown"
            elif file.filename.endswith(".msg"):
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


class MultipartMixedResponse(StreamingResponse):
    CRLF = b"\r\n"

    def __init__(self, *args, content_type: str = None, **kwargs):
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

    def _build_part_headers(self, headers: dict) -> bytes:
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


def ungz_file(file: UploadFile, gz_uncompressed_content_type=None) -> UploadFile:
    def return_content_type(filename):
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


@router.post("/general/v0/general")
@router.post("/general/v0.0.57/general")
def partition_parameters(
    request: Request,
    gz_uncompressed_content_type: Optional[str] = Form(default=None),
    files: Union[List[UploadFile], None] = File(default=None),
    output_format: Union[str, None] = Form(default=None),
    coordinates: List[str] = Form(default=[]),
    encoding: List[str] = Form(default=[]),
    hi_res_model_name: List[str] = Form(default=[]),
    include_page_breaks: List[str] = Form(default=[]),
    ocr_languages: List[str] = Form(default=None),
    pdf_infer_table_structure: List[str] = Form(default=[]),
    skip_infer_table_types: List[str] = Form(default=[]),
    strategy: List[str] = Form(default=[]),
    xml_keep_tags: List[str] = Form(default=[]),
    languages: List[str] = Form(default=None),
    chunking_strategy: List[str] = Form(default=[]),
    multipage_sections: List[str] = Form(default=[]),
    combine_under_n_chars: List[str] = Form(default=[]),
    new_after_n_chars: List[str] = Form(default=[]),
    max_characters: List[str] = Form(default=[]),
):
    if files:
        for file_index in range(len(files)):
            if files[file_index].content_type == "application/gzip":
                files[file_index] = ungz_file(files[file_index], gz_uncompressed_content_type)

    content_type = request.headers.get("Accept")

    default_response_type = output_format or "application/json"
    if not content_type or content_type == "*/*" or content_type == "multipart/mixed":
        media_type = default_response_type
    else:
        media_type = content_type

    if isinstance(files, list) and len(files):
        if len(files) > 1:
            if content_type and content_type not in [
                "*/*",
                "multipart/mixed",
                "application/json",
                "text/csv",
            ]:
                raise HTTPException(
                    detail=(
                        f"Conflict in media type {content_type}"
                        ' with response type "multipart/mixed".\n'
                    ),
                    status_code=status.HTTP_406_NOT_ACCEPTABLE,
                )

        def response_generator(is_multipart):
            for file in files:
                file_content_type = get_validated_mimetype(file)

                _file = file.file

                response = pipeline_api(
                    _file,
                    request=request,
                    m_coordinates=coordinates,
                    m_encoding=encoding,
                    m_hi_res_model_name=hi_res_model_name,
                    m_include_page_breaks=include_page_breaks,
                    m_ocr_languages=ocr_languages,
                    m_pdf_infer_table_structure=pdf_infer_table_structure,
                    m_skip_infer_table_types=skip_infer_table_types,
                    m_strategy=strategy,
                    m_xml_keep_tags=xml_keep_tags,
                    response_type=media_type,
                    filename=file.filename,
                    file_content_type=file_content_type,
                    languages=languages,
                    m_chunking_strategy=chunking_strategy,
                    m_multipage_sections=multipage_sections,
                    m_combine_under_n_chars=combine_under_n_chars,
                    m_new_after_n_chars=new_after_n_chars,
                    m_max_characters=max_characters,
                )

                if is_expected_response_type(media_type, type(response)):
                    raise HTTPException(
                        detail=(
                            f"Conflict in media type {media_type}"
                            f" with response type {type(response)}.\n"
                        ),
                        status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    )

                valid_response_types = ["application/json", "text/csv", "*/*", "multipart/mixed"]
                if media_type in valid_response_types:
                    if is_multipart:
                        if type(response) not in [str, bytes]:
                            response = json.dumps(response)
                    elif media_type == "text/csv":
                        response = PlainTextResponse(response)
                    yield response
                else:
                    raise HTTPException(
                        detail=f"Unsupported media type {media_type}.\n",
                        status_code=status.HTTP_406_NOT_ACCEPTABLE,
                    )

        def join_responses(responses):
            if media_type != "text/csv":
                return responses
            data = pd.read_csv(io.BytesIO(responses[0].body))
            if len(responses) > 1:
                for resp in responses[1:]:
                    resp_data = pd.read_csv(io.BytesIO(resp.body))
                    data = data.merge(resp_data, how="outer")
            return PlainTextResponse(data.to_csv())

        if content_type == "multipart/mixed":
            return MultipartMixedResponse(
                response_generator(is_multipart=True), content_type=media_type
            )
        else:
            return (
                list(response_generator(is_multipart=False))[0]
                if len(files) == 1
                else join_responses(list(response_generator(is_multipart=False)))
            )
    else:
        raise HTTPException(
            detail='Request parameter "files" is required.\n',
            status_code=status.HTTP_400_BAD_REQUEST,
        )


app.include_router(router)
