from __future__ import annotations

import io
import json
import os
from typing import List, Sequence, Dict, Any, cast, Union, Optional

import pandas as pd
from fastapi import APIRouter, UploadFile, Depends, HTTPException
from starlette import status
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from prepline_general.api.general import (
    ungz_file,
    MultipartMixedResponse,
    pipeline_api,
)
from prepline_general.api.validation import _validate_chunking_strategy, get_validated_mimetype
from prepline_general.api.models.form_params import GeneralFormParams

router = APIRouter()


@router.post(
    "/general/v0/general",
    openapi_extra={"x-speakeasy-name-override": "partition"},
    tags=["general"],
    summary="Summary",
    description="Description",
    operation_id="partition_parameters",
)
@router.post("/general/v0.0.68/general", include_in_schema=False)
def general_partition(
    request: Request,
    # cannot use annotated type here because of a bug described here:
    # https://github.com/tiangolo/fastapi/discussions/10280
    # The openapi metadata must be added separately in openapi.py file.
    # TODO: Check if the bug is fixed and change the declaration to use Annoteted[List[UploadFile], File(...)]
    # For new parameters - add them in models/form_params.py
    files: List[UploadFile],
    form_params: GeneralFormParams = Depends(GeneralFormParams.as_form),
):
    # -- must have a valid API key --
    if api_key_env := os.environ.get("UNSTRUCTURED_API_KEY"):
        api_key = request.headers.get("unstructured-api-key")
        if api_key != api_key_env:
            raise HTTPException(
                detail=f"API key {api_key} is invalid", status_code=status.HTTP_401_UNAUTHORIZED
            )

    content_type = request.headers.get("Accept")

    # -- detect response content-type conflict when multiple files are uploaded --
    if (
        len(files) > 1
        and content_type
        and content_type
        not in [
            "*/*",
            "multipart/mixed",
            "application/json",
            "text/csv",
        ]
    ):
        raise HTTPException(
            detail=f"Conflict in media type {content_type} with response type 'multipart/mixed'.\n",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )

    # -- validate other arguments --
    chunking_strategy = _validate_chunking_strategy(form_params.chunking_strategy)

    # -- unzip any uploaded files that need it --
    for idx, file in enumerate(files):
        is_content_type_gz = file.content_type == "application/gzip"
        is_extension_gz = file.filename and file.filename.endswith(".gz")
        if is_content_type_gz or is_extension_gz:
            files[idx] = ungz_file(file, form_params.gz_uncompressed_content_type)

    return (
        MultipartMixedResponse(
            response_generator(files, request, form_params, chunking_strategy, is_multipart=True),
            content_type=form_params.output_format,
        )
        if content_type == "multipart/mixed"
        else (
            list(
                response_generator(
                    files, request, form_params, chunking_strategy, is_multipart=False
                )
            )[0]
            if len(files) == 1
            else join_responses(
                form_params,
                list(
                    response_generator(
                        files, request, form_params, chunking_strategy, is_multipart=False
                    )
                ),
            )
        )
    )


def join_responses(
    form_params: GeneralFormParams,
    responses: Sequence[str | List[Dict[str, Any]] | PlainTextResponse],
) -> List[str | List[Dict[str, Any]]] | PlainTextResponse:
    """Consolidate partitionings from multiple documents into single response payload."""
    if form_params.output_format != "text/csv":
        return cast(List[Union[str, List[Dict[str, Any]]]], responses)
    responses = cast(List[PlainTextResponse], responses)
    data = pd.read_csv(io.BytesIO(responses[0].body))  # pyright: ignore[reportUnknownMemberType]
    if len(responses) > 1:
        for resp in responses[1:]:
            resp_data = pd.read_csv(  # pyright: ignore[reportUnknownMemberType]
                io.BytesIO(resp.body)
            )
            data = data.merge(resp_data, how="outer")  # pyright: ignore[reportUnknownMemberType]
    return PlainTextResponse(data.to_csv())


def response_generator(
    files: List[UploadFile],
    request: Request,
    form_params: GeneralFormParams,
    chunking_strategy: Optional[str],
    is_multipart: bool,
):
    for file in files:
        file_content_type = get_validated_mimetype(file)
        _file = file.file

        response = pipeline_api(
            _file,
            request=request,
            coordinates=form_params.coordinates,
            encoding=form_params.encoding,
            hi_res_model_name=form_params.hi_res_model_name,
            include_page_breaks=form_params.include_page_breaks,
            ocr_languages=form_params.ocr_languages,
            pdf_infer_table_structure=form_params.pdf_infer_table_structure,
            skip_infer_table_types=form_params.skip_infer_table_types,
            strategy=form_params.strategy,
            xml_keep_tags=form_params.xml_keep_tags,
            response_type=form_params.output_format,
            filename=str(file.filename),
            file_content_type=file_content_type,
            languages=form_params.languages,
            extract_image_block_types=form_params.extract_image_block_types,
            unique_element_ids=form_params.unique_element_ids,
            # -- chunking options --
            chunking_strategy=chunking_strategy,
            combine_under_n_chars=form_params.combine_under_n_chars,
            max_characters=form_params.max_characters,
            multipage_sections=form_params.multipage_sections,
            new_after_n_chars=form_params.new_after_n_chars,
            overlap=form_params.overlap,
            overlap_all=form_params.overlap_all,
            starting_page_number=form_params.starting_page_number,
        )

        yield (
            json.dumps(response)
            if is_multipart and type(response) not in [str, bytes]
            else (
                PlainTextResponse(response)
                if not is_multipart and form_params.output_format == "text/csv"
                else response
            )
        )


@router.get("/general/v0/general", include_in_schema=False)
@router.get("/general/v0.0.68/general", include_in_schema=False)
async def handle_invalid_get_request():
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Only POST requests are supported."
    )


@router.get("/healthcheck", status_code=status.HTTP_200_OK, include_in_schema=False)
def healthcheck(request: Request):
    return {"healthcheck": "HEALTHCHECK STATUS: EVERYTHING OK!"}
