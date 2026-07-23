import asyncio
import io
from base64 import b64encode

import orjson
import pytest
from fastapi.testclient import TestClient

from prepline_general.api import general
from prepline_general.api.app import app
from prepline_general.api.general import MultipartMixedResponse


def test_multipart_response_sends_framing_and_payload_separately():
    response = MultipartMixedResponse(
        iter([b"serialized response"]), content_type="application/json"
    )
    events = []

    async def send(event):
        events.append(event)

    asyncio.run(response.stream_response(send))

    body_events = [event for event in events if event["type"] == "http.response.body"]
    encoded_payload = b64encode(b"serialized response")

    assert body_events[0]["body"].startswith(response.boundary)
    assert f"Content-Length: {len(encoded_payload)}".encode() in body_events[0]["body"]
    assert body_events[1]["body"] == encoded_payload
    assert body_events[2]["body"] == response.CRLF
    assert body_events[3] == {
        "type": "http.response.body",
        "body": b"",
        "more_body": False,
    }


@pytest.mark.parametrize("file_count", [1, 2])
def test_json_endpoint_serializes_response_directly_to_bytes(monkeypatch, file_count):
    file_response = [{"text": "partitioned text", "metadata": {}}]
    monkeypatch.delenv("UNSTRUCTURED_API_KEY", raising=False)
    monkeypatch.setattr(general, "get_validated_mimetype", lambda *args, **kwargs: "text/plain")
    monkeypatch.setattr(general, "pipeline_api", lambda *args, **kwargs: file_response)
    files = [
        ("files", (f"sample-{idx}.txt", io.BytesIO(b"sample"), "text/plain"))
        for idx in range(file_count)
    ]

    response = TestClient(app).post("/general/v0/general", files=files)

    expected = file_response if file_count == 1 else [file_response] * file_count
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.content == orjson.dumps(expected)
