from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import UploadFile

from prepline_general.api import filetypes
from unstructured.file_utils.model import FileType


def test_unknown_mimetype_is_detected_from_existing_upload_stream(monkeypatch):
    upload_stream = SpooledTemporaryFile()
    upload_stream.write(b"sample text")
    upload_stream.seek(0)
    upload = UploadFile(file=upload_stream, filename="sample.txt")

    def fake_detect_filetype(*, file, metadata_file_path):
        assert file is upload_stream
        assert metadata_file_path == "sample.txt"
        file.seek(4)
        return FileType.TXT

    monkeypatch.setattr(filetypes, "detect_filetype", fake_detect_filetype)

    assert filetypes.get_validated_mimetype(upload) == "text/plain"
    assert upload_stream.tell() == 0


def test_unknown_mimetype_rewinds_upload_stream_when_detection_fails(monkeypatch):
    upload_stream = SpooledTemporaryFile()
    upload_stream.write(b"sample text")
    upload_stream.seek(0)
    upload = UploadFile(file=upload_stream, filename="sample.txt")

    def fake_detect_filetype(*, file, metadata_file_path):
        file.seek(4)
        raise RuntimeError("detection failed")

    monkeypatch.setattr(filetypes, "detect_filetype", fake_detect_filetype)

    with pytest.raises(RuntimeError, match="detection failed"):
        filetypes.get_validated_mimetype(upload)

    assert upload_stream.tell() == 0


def _assert_matches_copied_upload(filename: str | None, payload: bytes, max_size: int):
    copied = BytesIO(payload)
    copied.name = filename
    expected = filetypes.detect_filetype(file=copied)
    with SpooledTemporaryFile(max_size=max_size) as stream:
        stream.write(payload)
        stream.seek(0)
        upload = UploadFile(file=stream, filename=filename)
        assert filetypes.get_validated_mimetype(upload) == expected.mime_type
        assert stream.tell() == 0
        assert not stream.closed


@pytest.mark.parametrize("max_size", [1, 1024 * 1024])
@pytest.mark.parametrize(
    "filename,payload",
    [
        ("sample.txt", b"A sample paragraph of ordinary text."),
        ("sample.html", b"<!doctype html><html><body><p>Hello</p></body></html>"),
        ("sample.csv", b"name,value\nAlice,1\nBob,2\n"),
        ("sample.json", b'{"name": "Alice", "value": 1}'),
        (None, b"A sample paragraph of ordinary text."),
    ],
)
def test_real_detector_matches_copied_upload(filename, payload, max_size):
    _assert_matches_copied_upload(filename, payload, max_size)


@pytest.mark.parametrize("filename", ["layout-parser-paper.pdf", "notes.pptx", "stanley-cups.xlsx"])
@pytest.mark.parametrize("max_size", [1, 10 * 1024 * 1024])
def test_real_detector_matches_copied_binary_upload(filename, max_size):
    payload = (Path("sample-docs") / filename).read_bytes()
    _assert_matches_copied_upload(filename, payload, max_size)
