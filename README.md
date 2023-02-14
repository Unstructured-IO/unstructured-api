<h3 align="center">
  <img src="img/unstructured_logo.png" height="200">
</h3>

<h3 align="center">
  <p>General Pre-Processing Pipeline for Documents</p>
</h3>


This repo implements a pre-processing pipeline for `.txt`, `.docx`, `.pptx`, `.jpg`, `.png`, `.eml`, `.html`, and `.pdf` documents. Currently, the pipeline is capable of recognizing the file type and choosing the relevant partition function to process the file.

The API is hosted at `https://api.unstructured.io`.


## Developer Quick Start

* Using `pyenv` to manage virtualenv's is recommended
	* Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
		* `brew install pyenv-virtualenv`
	  * `pyenv install 3.8.15`
  * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

  * Create a virtualenv to work in and activate it, e.g. for one named `document-processing`:

	`pyenv  virtualenv 3.8.15 document-processing` <br />
	`pyenv activate document-processing`

* Run `make install`
* Start a local jupyter notebook server with `make run-jupyter` <br />
	**OR** <br />
	just start the fast-API locally with `make run-web-app`

#### Extracting whatever from some type of document

Give a description of making API calls using example `curl` commands, and example JSON responses.

For example:
```
 curl -X 'POST' \
  'http://localhost:8000/documents/v0.0.2/documents' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@family_day.eml' \
  | jq -C . | less -R
```

It's also nice to show how to call the API function using pure Python.

### Generating Python files from the pipeline notebooks

You can generate the FastAPI APIs from your pipeline notebooks by running `make generate-api`.

## Security Policy

See our [security policy](https://github.com/Unstructured-IO/pipeline-emails/security/policy) for
information on how to report security vulnerabilities.

## Learn more

| Section | Description |
|-|-|
| [Unstructured Community Github](https://github.com/Unstructured-IO/community) | Information about Unstructured.io community projects  |
| [Unstructured Github](https://github.com/Unstructured-IO) | Unstructured.io open source repositories |
| [Company Website](https://unstructured.io) | Unstructured.io product and company info |
