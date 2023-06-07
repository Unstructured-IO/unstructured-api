<h3 align="center">
  <img src="img/unstructured_logo.png" height="200">
</h3>

<h3 align="center">
  <p>General Pre-Processing Pipeline for Documents</p>
</h3>

This repo implements a pre-processing pipeline for the following documents. Currently, the pipeline is capable of recognizing the file type and choosing the relevant partition function to process the file.

* Plaintext: `.txt`, `.eml`, `.html`, `.md`, `.json`, `.rtf`
* Images: `.jpeg`, `.png`
* Documents: `.doc`, `.docx`, `.ppt`, `.pptx`, `.pdf`, `.odt`, `.epub`

## :rocket: Unstructured API

Try our hosted API! It's freely available to use with any of the filetypes listed above. This is the easiest way to get started. If you'd like to host your own version of the API, jump down to the [Developer Quickstart Guide](#developer-quick-start).

```
 curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@sample-docs/family-day.eml' \
  | jq -C . | less -R
```

### Parameters

#### PDF Strategies

Three strategies are available for processing PDF files: `hi_res`, `fast`, and `auto`. `fast` is the default `strategy` and works well for documents that do not have text embedded in images.

On the other hand, `hi_res` is the better choice for PDF's that may have text within embedded images, or for achieving greater precision of [element types](https://unstructured-io.github.io/unstructured/getting_started.html#document-elements) in the response JSON. Please be aware that, as of writing, `hi_res` requests may take 20 times longer to process compared to the`fast` option. See the example below for making a `hi_res` request.

For the best of both worlds, `auto` will determine when a page can be extracted using `fast` mode, otherwise it will fall back to `hi_res`.

```
 curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@sample-docs/layout-parser-paper.pdf' \
  -F 'strategy=hi_res' \
  | jq -C . | less -R
```

#### Coordinates

When elements are extracted from PDFs or images, it may be useful to get their bounding boxes as well. Set the `coordinates` parameter to `true` to add this field to the elements in the response.

```
 curl -X 'POST' \
  'https://api.unstructured.io/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@sample-docs/layout-parser-paper.pdf' \
  -F 'coordinates=true' \
  | jq -C . | less -R
```


## Developer Quick Start

* Using `pyenv` to manage virtualenv's is recommended
	* Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
		* `brew install pyenv-virtualenv`
	  * `pyenv install 3.8.15`
  * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

  * Create a virtualenv to work in and activate it, e.g. for one named `document-processing`:

	`pyenv  virtualenv 3.8.15 document-processing` <br />
	`pyenv activate document-processing`

See the [Unstructured Quick Start](https://github.com/Unstructured-IO/unstructured#eight_pointed_black_star-quick-start) for the many OS dependencies that are required, if the ability to process all file types is desired.

* Run `make install`
* If image and high resolution pdf extraction is required, also run `make install-high`
* Start a local jupyter notebook server with `make run-jupyter` <br />
	**OR** <br />
	just start the fast-API locally with `make run-web-app`

#### Using the API locally

After running `make run-web-app` (or `make docker-start-api` to run in the container), you can now hit the API locally at port 8000. The `sample-docs` directory has a number of example file types that are currently supported.

For example:
```
 curl -X 'POST' \
  'http://localhost:8000/general/v0/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@sample-docs/family-day.eml' \
  | jq -C . | less -R
```

The response will be a list of the extracted elements:
```
[
  {
    "element_id": "db1ca22813f01feda8759ff04a844e56",
    "coordinates": null,
    "text": "Hi All,",
    "type": "UncategorizedText",
    "metadata": {
      "date": "2022-12-21T10:28:53-06:00",
      "sent_from": [
        "Mallori Harrell <mallori@unstructured.io>"
      ],
      "sent_to": [
        "Mallori Harrell <mallori@unstructured.io>"
      ],
      "subject": "Family Day",
      "filename": "family-day.eml"
    }
  },
...
...
```

#### Parallel Mode for PDFs
As mentioned above, processing a pdf using `hi_res` is currently a slow operation. One workaround is to split the pdf into smaller files, process these asynchronously, and merge the results. You can enable parallel processing mode with the following env variables:

* `UNSTRUCTURED_PARALLEL_MODE_ENABLED` - set to `true` to process individual pdf pages remotely 
* `UNSTRUCTURED_PARALLEL_MODE_URL` - the location to send pdf page asynchronously

### Generating Python files from the pipeline notebooks

You can generate the FastAPI APIs from your pipeline notebooks by running `make generate-api`.

## :dizzy: Instructions for using the Docker image

The following instructions are intended to help you get up and running using Docker to interact with `unstructured-api`.
See [here](https://docs.docker.com/get-docker/) if you don't already have docker installed on your machine.

NOTE: we build multi-platform images to support both x86_64 and Apple silicon hardware. Docker pull should download the corresponding image for your architecture, but you can specify with `--platform` (e.g. --platform linux/amd64) if needed.

We build Docker images for all pushes to `main`. We tag each image with the corresponding short commit hash (e.g. `fbc7a69`) and the application version (e.g. `0.5.5-dev1`). We also tag the most recent image with `latest`. To leverage this, `docker pull` from our image repository.

```bash
docker pull quay.io/unstructured-io/unstructured-api:latest
```

Once pulled, you can launch the container as a web app on localhost:8000.

```bash
docker run -p 8000:8000 -d --rm --name unstructured-api quay.io/unstructured-io/unstructured-api:latest --port 8000 --host 0.0.0.0
```

## Security Policy

See our [security policy](https://github.com/Unstructured-IO/pipeline-emails/security/policy) for
information on how to report security vulnerabilities.

## Learn more

| Section | Description |
|-|-|
| [Unstructured Community Github](https://github.com/Unstructured-IO/community) | Information about Unstructured.io community projects  |
| [Unstructured Github](https://github.com/Unstructured-IO) | Unstructured.io open source repositories |
| [Company Website](https://unstructured.io) | Unstructured.io product and company info |
