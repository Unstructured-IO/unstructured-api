import asyncio
from email import policy
from email.parser import BytesParser

import pytest

from prepline_general.api.general import MultipartMixedResponse


async def collect_response(response):
    messages = []

    async def send(message):
        messages.append(message)

    await response.stream_response(send)
    return messages


@pytest.mark.parametrize("parts", [["one"], ["one", "two"]])
def test_normal_multipart_response_closes_boundary_and_preserves_parts(parts):
    response = MultipartMixedResponse(iter(parts), content_type="text/plain")
    messages = asyncio.run(collect_response(response))
    body = b"".join(message.get("body", b"") for message in messages)
    content_type = response.headers["content-type"].encode()
    parsed = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )

    assert parsed.defects == []
    assert [part.get_payload(decode=True).decode() for part in parsed.iter_parts()] == parts
    assert messages[-1] == {
        "type": "http.response.body",
        "body": response.boundary + b"--\r\n",
        "more_body": False,
    }
    assert all(message["more_body"] for message in messages[1:-1])


def test_empty_iterator_emits_terminal_boundary():
    response = MultipartMixedResponse(iter([]))
    messages = asyncio.run(collect_response(response))

    assert messages[-1]["body"] == response.boundary + b"--\r\n"
    assert messages[-1]["more_body"] is False


def test_interrupted_stream_does_not_emit_terminal_boundary():
    messages = []

    async def failing_parts():
        yield "one"
        raise RuntimeError("partition failed")

    async def send(message):
        messages.append(message)

    response = MultipartMixedResponse(failing_parts(), content_type="text/plain")
    with pytest.raises(RuntimeError, match="partition failed"):
        asyncio.run(response.stream_response(send))

    assert len(messages) == 2
    assert messages[-1]["more_body"] is True
    assert not messages[-1]["body"].endswith(response.boundary + b"--\r\n")
