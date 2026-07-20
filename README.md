<p align="center">
  <img src="img/unstructured_logo.svg" width="120" alt="Unstructured">
</p>

# Unstructured API

A self-hosted REST API for partitioning documents with the
[`unstructured`](https://github.com/Unstructured-IO/unstructured) open-source library. The API
detects the uploaded file type, selects the corresponding partitioner, and returns document
elements as JSON or CSV.

This repository is for running the Partition Endpoint yourself. For Unstructured's managed API,
current platform features, and hosted quickstarts, see the
[Unstructured API documentation](https://docs.unstructured.io/api-reference/overview).

## What it supports

- The partitionable document types supported by the pinned `unstructured[all-docs]` dependency.
  See the current
  [open-source supported file types](https://docs.unstructured.io/open-source/introduction/supported-file-types).
- PDF and image strategies: `auto`, `fast`, `hi_res`, and `ocr_only`.
- Optional table and image-block extraction, OCR language selection, page breaks, coordinates,
  deterministic or UUID element IDs, and gzip uploads.
- `by_title` chunking, including overlap controls and optional original-element metadata.
- Single-file and multi-file requests, with JSON, CSV, or `multipart/mixed` responses.

The generated API reference lists the complete request schema. After starting the server, open
[http://localhost:8000/general/docs](http://localhost:8000/general/docs), or read the OpenAPI document at
[http://localhost:8000/general/openapi.json](http://localhost:8000/general/openapi.json).

## Local quickstart

### Requirements

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- The system dependencies required by the document types you plan to process. See the
  [`unstructured` installation guide](https://docs.unstructured.io/open-source/installation/full-installation).

Install the locked runtime and test dependencies, then start the development server:

```bash
make install
make run-web-app
```

The API listens on `http://localhost:8000`. Verify it is ready:

```bash
curl --fail http://localhost:8000/healthcheck
```

Partition a sample document:

```bash
curl --request POST \
  --url http://localhost:8000/general/v0/general \
  --header 'accept: application/json' \
  --form 'files=@sample-docs/family-day.eml'
```

The response is a list of document elements:

```json
[
  {
    "element_id": "db1ca22813f01feda8759ff04a844e56",
    "text": "Hi All,",
    "type": "UncategorizedText",
    "metadata": {
      "filename": "family-day.eml"
    }
  }
]
```

### Common options

The default PDF/image strategy is `auto`. For layout-aware partitioning, request `hi_res`:

```bash
curl --request POST \
  --url http://localhost:8000/general/v0/general \
  --header 'accept: application/json' \
  --form 'files=@sample-docs/layout-parser-paper.pdf' \
  --form 'strategy=hi_res'
```

Use `languages` to specify OCR languages. The older `ocr_languages` parameter remains available
for compatibility but is deprecated by the underlying library.

```bash
curl --request POST \
  --url http://localhost:8000/general/v0/general \
  --header 'accept: application/json' \
  --form 'files=@sample-docs/english-and-korean.png' \
  --form 'strategy=ocr_only' \
  --form 'languages=eng' \
  --form 'languages=kor'
```

Chunk the output by document title. Original elements are included in chunk metadata by default;
set `include_orig_elements=false` when you want a smaller response:

```bash
curl --request POST \
  --url http://localhost:8000/general/v0/general \
  --header 'accept: application/json' \
  --form 'files=@sample-docs/layout-parser-paper-fast.pdf' \
  --form 'chunking_strategy=by_title' \
  --form 'max_characters=1500' \
  --form 'include_orig_elements=false'
```

Return CSV instead of JSON:

```bash
curl --request POST \
  --url http://localhost:8000/general/v0/general \
  --header 'accept: text/csv' \
  --form 'files=@sample-docs/family-day.eml' \
  --form 'output_format=text/csv'
```

## Docker

### Run the published image

Multi-platform images for `amd64` and `arm64` are published to Quay:

```bash
docker pull quay.io/unstructured-io/unstructured-api:latest
docker run --rm --name unstructured-api -p 8000:8000 \
  quay.io/unstructured-io/unstructured-api:latest
```

Pin a release or commit tag instead of `latest` for reproducible deployments.

### Build locally

```bash
make docker-build
make docker-start-api
```

## Server configuration

| Variable | Default | Description |
|---|---:|---|
| `PORT` | `8000` | Port used by the container entrypoint. |
| `HOST` | `0.0.0.0` | Interface used by the container entrypoint. |
| `WORKERS` | `1` | Number of Uvicorn workers. |
| `UNSTRUCTURED_API_KEY` | unset | When set, requests must supply the same value in the `unstructured-api-key` header. |
| `UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB` | `2048` | Reject new work with HTTP 503 below this amount of free memory. Set to `0` to disable the check. |
| `ALLOWED_ORIGINS` | unset | Comma-separated origins allowed by the optional CORS middleware. |
| `MAX_LIFETIME_SECONDS` | unset | Begin graceful shutdown after this many seconds: new requests are denied while in-flight requests finish, then the server exits (forcefully after at most 3600 seconds). Requires GNU `timeout` (`gtimeout` on macOS). |

### Parallel PDF mode

Parallel mode splits PDFs into page ranges, sends those ranges to another Partition Endpoint, and
combines the results. It is most useful for `hi_res` workloads.

| Variable | Default | Description |
|---|---:|---|
| `UNSTRUCTURED_PARALLEL_MODE_ENABLED` | `false` | Set to `true` to enable remote page processing. |
| `UNSTRUCTURED_PARALLEL_MODE_URL` | unset | Partition Endpoint URL that receives page ranges. Required when parallel mode is enabled. |
| `UNSTRUCTURED_PARALLEL_MODE_THREADS` | `3` | Maximum concurrent remote requests. |
| `UNSTRUCTURED_PARALLEL_MODE_SPLIT_SIZE` | `1` | Pages per remote request. |
| `UNSTRUCTURED_PARALLEL_RETRY_ATTEMPTS` | `2` | Retries after the initial request for retryable errors. |

Alternatively, the official
[Python client](https://github.com/Unstructured-IO/unstructured-python-client?tab=readme-ov-file#splitting-pdf-by-pages)
can split PDFs client-side with `split_pdf_page=True`.

## Development

Install the locked development environment:

```bash
make install
```

Run the checks and test suite:

```bash
make check
make test
```

See the
[Unstructured contribution guide](https://github.com/Unstructured-IO/unstructured/blob/main/CONTRIBUTING.md)
before opening a pull request.

## Security

Report vulnerabilities through this repository's
[security policy](https://github.com/Unstructured-IO/unstructured-api/security/policy).

## License

Licensed under the [Apache License 2.0](LICENSE.md).
