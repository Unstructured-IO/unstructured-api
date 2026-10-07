import io
from unittest.mock import Mock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from prepline_general.api import general
from prepline_general.api.models.form_params import GeneralFormParams
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import NarrativeText, Title


def test_parallel_worker_honors_nondefault_combine_threshold(monkeypatch):
    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_URL", "https://worker.example/partition")
    worker = FastAPI()
    received_forms = []
    received_params = []

    @worker.post("/partition")
    def partition_worker(params: GeneralFormParams = Depends(GeneralFormParams.as_form)):
        received_params.append(params)
        elements = [
            Title("First section"),
            NarrativeText("A short paragraph."),
            Title("Second section"),
            NarrativeText("Another short paragraph."),
        ]
        chunks = chunk_by_title(
            elements,
            max_characters=params.max_characters,
            combine_text_under_n_chars=params.combine_under_n_chars,
        )
        return [chunk.to_dict() for chunk in chunks]

    client = TestClient(worker)

    def post_to_worker(url, *, files, data, headers):
        received_forms.append(data.copy())
        return client.post("/partition", files=files, data=data, headers=headers)

    monkeypatch.setattr(general.requests, "post", post_to_worker)
    request = Request({"type": "http", "headers": []})
    options = {
        "chunking_strategy": "by_title",
        "max_characters": 500,
        "combine_text_under_n_chars": 0,
        "starting_page_number": 2,
    }

    chunks = general.partition_file_via_api(
        (io.BytesIO(b"pdf"), 3), request, "document.pdf", "application/pdf", **options
    )
    combined_chunks = general.partition_file_via_api(
        (io.BytesIO(b"pdf"), 3),
        request,
        "document.pdf",
        "application/pdf",
        **{**options, "combine_text_under_n_chars": 100},
    )

    assert len(chunks) == 2
    assert len(combined_chunks) == 1
    assert received_params[0].combine_under_n_chars == 0
    assert received_forms[0]["combine_under_n_chars"] == 0
    assert "combine_text_under_n_chars" not in received_forms[0]
    assert received_forms[0]["starting_page_number"] == 5
    assert options["starting_page_number"] == 2
    assert options["combine_text_under_n_chars"] == 0


def test_small_pdf_keeps_local_library_option(monkeypatch):
    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_SPLIT_SIZE", "2")
    local_partition = Mock(return_value=[])
    monkeypatch.setattr(general, "partition", local_partition)
    options = {"combine_text_under_n_chars": 0}
    file = io.BytesIO(b"pdf")
    request = Request({"type": "http", "headers": []})

    general.partition_pdf_splits(
        request, [Mock()], file, "document.pdf", "application/pdf", False, **options
    )

    local_partition.assert_called_once_with(
        file=file,
        metadata_filename="document.pdf",
        content_type="application/pdf",
        combine_text_under_n_chars=0,
    )
    assert options == {"combine_text_under_n_chars": 0}
