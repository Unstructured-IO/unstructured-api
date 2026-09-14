import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "parallel-mode-test.sh"


@pytest.fixture
def run_comparisons(tmp_path):
    curl = tmp_path / "curl"
    curl.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['REQUEST_LOG'], 'a') as log:\n"
        "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if os.environ.get('HTTP_FAILURE'):\n"
        "    sys.exit(22)\n"
        "body = os.environ.get('RESPONSE_BODY', '[{\"text\": \"content\"}]')\n"
        "if os.environ.get('MISMATCH') and any('parallel/' in arg for arg in sys.argv):\n"
        "    body = '[{}, {}]'\n"
        "print(body)\n"
    )
    curl.chmod(0o755)
    log = tmp_path / "requests.jsonl"

    def run(**overrides):
        result = subprocess.run(
            ["bash", str(SCRIPT), "http://single", "http://parallel"],
            env={
                **os.environ,
                "PATH": f"{tmp_path}:{os.environ['PATH']}",
                "REQUEST_LOG": str(log),
                **overrides,
            },
            capture_output=True,
            text=True,
            check=False,
        )
        requests = [json.loads(line) for line in log.read_text().splitlines()]
        return result, requests

    return run


def test_comparisons_send_valid_options_to_both_servers(run_comparisons):
    result, requests = run_comparisons()
    assert result.returncode == 0, result.stderr
    assert len(requests) == 14
    expected = [
        {"strategy": "fast"},
        {"strategy": "auto"},
        {"strategy": "hi_res"},
        {"strategy": "fast", "coordinates": "true"},
        {"strategy": "fast", "encoding": "utf-8"},
        {"strategy": "fast", "include_page_breaks": "true"},
        {"strategy": "hi_res", "hi_res_model_name": "yolox"},
    ]
    for index, args in enumerate(requests):
        fields = dict(args[i + 1].split("=", 1) for i, arg in enumerate(args) if arg == "-F")
        assert fields.pop("files") == "@sample-docs/layout-parser-paper.pdf"
        assert fields == expected[index // 2]
        server = "single" if index % 2 == 0 else "parallel"
        assert f"http://{server}/general/v0/general" in args
        assert "--fail" in args


@pytest.mark.parametrize("body", ['{"detail": "server error"}', "[]", "invalid JSON"])
def test_comparisons_reject_invalid_responses(run_comparisons, body):
    result, requests = run_comparisons(RESPONSE_BODY=body)
    assert result.returncode != 0
    assert len(requests) == 1


def test_comparisons_reject_http_failure(run_comparisons):
    result, requests = run_comparisons(HTTP_FAILURE="1")
    assert result.returncode != 0
    assert len(requests) == 1


def test_comparisons_reject_different_element_counts(run_comparisons):
    result, requests = run_comparisons(MISMATCH="1")
    assert result.returncode != 0
    assert len(requests) == 2
    assert "different number of elements" in result.stdout
