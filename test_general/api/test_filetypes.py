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

    def fake_detect_filetype(*, file):
        assert file._file is upload_stream
        assert file.name == "sample.txt"
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

    def fake_detect_filetype(*, file):
        file.seek(4)
        raise RuntimeError("detection failed")

    monkeypatch.setattr(filetypes, "detect_filetype", fake_detect_filetype)

    with pytest.raises(RuntimeError, match="detection failed"):
        filetypes.get_validated_mimetype(upload)

    assert upload_stream.tell() == 0
