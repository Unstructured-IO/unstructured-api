import io
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from prepline_general.api import general
from prepline_general.api.app import app
from unstructured.partition.utils.constants import OCR_AGENT_PADDLE, OCR_AGENT_TESSERACT

MAIN_API_ROUTE = "general/v0/general"


@pytest.mark.parametrize(
    ("env_value", "expected_agent"),
    [
        (None, OCR_AGENT_TESSERACT),
        (OCR_AGENT_PADDLE, OCR_AGENT_PADDLE),
        # -- legacy key-name form is mapped to the qualified name --
        ("paddle", OCR_AGENT_PADDLE),
    ],
)
def test_ocr_agent_env_var_is_passed_to_partition(monkeypatch, env_value, expected_agent):
    if env_value is None:
        monkeypatch.delenv("OCR_AGENT", raising=False)
    else:
        monkeypatch.setenv("OCR_AGENT", env_value)
    mock_partition = Mock(return_value=[])
    monkeypatch.setattr(general, "partition", mock_partition)

    client = TestClient(app)
    test_file = Path("sample-docs") / "layout-parser-paper-fast.jpg"
    with open(test_file, "rb") as f:
        response = client.post(
            MAIN_API_ROUTE,
            files=[("files", (str(test_file), f, "image/jpeg"))],
            data={"strategy": "hi_res"},
        )

    assert response.status_code == 200
    mock_partition.assert_called_once()
    assert mock_partition.call_args.kwargs["ocr_agent"] == expected_agent


def test_ocr_agent_is_not_sent_to_parallel_workers(monkeypatch):
    monkeypatch.setenv("UNSTRUCTURED_PARALLEL_MODE_URL", "https://worker.example/partition")
    post = Mock(return_value=Mock(status_code=200, text="[]"))
    monkeypatch.setattr(general.requests, "post", post)
    request = Request({"type": "http", "headers": []})

    general.partition_file_via_api(
        (io.BytesIO(b"pdf"), 0),
        request,
        "document.pdf",
        "application/pdf",
        strategy="hi_res",
        ocr_agent=OCR_AGENT_PADDLE,
    )

    sent_form = post.call_args.kwargs["data"]
    assert sent_form["strategy"] == "hi_res"
    assert "ocr_agent" not in sent_form
