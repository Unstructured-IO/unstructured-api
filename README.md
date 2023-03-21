<h3 align="center">
  <img src="img/unstructured_logo.png" height="200">
</h3>

<h3 align="center">
  <p>General Pre-Processing Pipeline for Documents</p>
</h3>

This repo implements a pre-processing pipeline for the following documents. Currently, the pipeline is capable of recognizing the file type and choosing the relevant partition function to process the file.

* Various plaintext files: `.txt`, `.eml`, `.html`, `.md`, `.json`
* Images: `.jpeg`, `.png`
* Documents: `.doc`, `.docx`, `.ppt`, `.pptx`, `.pdf`, `.epub`

## Developer Quick Start

* Using `pyenv` to manage virtualenv's is recommended
	* Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
		* `brew install pyenv-virtualenv`
	  * `pyenv install 3.8.15`
  * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

  * Create a virtualenv to work in and activate it, e.g. for one named `document-processing`:

	`pyenv  virtualenv 3.8.15 document-processing` <br />
	`pyenv activate document-processing`

# See the [Unstructured Quick Start](https://github.com/Unstructured-IO/unstructured#eight_pointed_black_star-quick-start) for the many OS dependencies that are required, if the ability to process all file types is desired.
* Run `make install`
* Start a local jupyter notebook server with `make run-jupyter` <br />
	**OR** <br />
	just start the fast-API locally with `make run-web-app`

#### Extracting whatever from some type of document

Give a description of making API calls using example `curl` commands, and example JSON responses.

For example:
```
 curl -X 'POST' \
  'http://localhost:8000/general/v0.0.4/general' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@family-day.eml' \
  | jq -C . | less -R
```

It's also nice to show how to call the API function using pure Python.

### Generating Python files from the pipeline notebooks

You can generate the FastAPI APIs from your pipeline notebooks by running `make generate-api`.

## :dizzy: Instructions for using the Docker image

The following instructions are intended to help you get up and running using Docker to interact with `unstructured-api`.
See [here](https://docs.docker.com/get-docker/) if you don't already have docker installed on your machine.

NOTE: the image is only supported for x86_64 hardware and known to have issues on Apple silicon. Known issues are specific to processing files that need to use inference, i.e. .jpeg and .pdf. When running the amd64 container on a mac, this results in an unsupported hardware error that causes the server to hang.

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
