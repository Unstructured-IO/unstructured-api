import io
from unittest.mock import Mock

import pytest
import requests
from fastapi import HTTPException

from prepline_general.api import general


def worker_response(status, body):
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.encoding = "utf-8"
    return response


def call_worker():
    return general.call_api(
        "https://worker.example/general/v0/general",
        "key",
        "document.pdf",
        io.BytesIO(b"pdf"),
        "application/pdf",
    )


@pytest.mark.parametrize("body", [b"Service unavailable", b"<html>Unavailable</html>"])
def test_transient_non_json_worker_errors_are_retried(monkeypatch, body):
    post = Mock(side_effect=[worker_response(503, body), worker_response(200, b"[]")])
    monkeypatch.setattr(general.requests, "post", post)
    monkeypatch.setattr("backoff._sync.time.sleep", lambda _: None)

    assert call_worker() == "[]"
    assert post.call_count == 2


@pytest.mark.parametrize(
    "body, expected_detail",
    [
        (b'{"detail":"Invalid document"}', "Invalid document"),
        (b'{"detail":{"reason":"Invalid document"}}', {"reason": "Invalid document"}),
        (b'{"detail":""}', '{"detail":""}'),
        (b"{}", "{}"),
        (b"[]", "[]"),
        (b'"Invalid document"', '"Invalid document"'),
        (b"42", "42"),
        (b"null", "null"),
        (b"", ""),
        (b"Invalid document", "Invalid document"),
    ],
)
def test_worker_client_errors_preserve_status_and_detail_without_retry(
    monkeypatch, body, expected_detail
):
    post = Mock(return_value=worker_response(422, body))
    monkeypatch.setattr(general.requests, "post", post)

    with pytest.raises(HTTPException) as exc_info:
        call_worker()

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == expected_detail
    assert post.call_count == 1


def test_non_json_server_errors_preserve_status_after_retry_exhaustion(monkeypatch):
    post = Mock(return_value=worker_response(503, b"Service unavailable"))
    monkeypatch.setattr(general.requests, "post", post)
    monkeypatch.setattr("backoff._sync.time.sleep", lambda _: None)

    with pytest.raises(HTTPException) as exc_info:
        call_worker()

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service unavailable"
    assert post.call_count == 3
