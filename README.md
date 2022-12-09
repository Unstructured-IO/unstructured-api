<h3 align="center">
  <img src="img/unstructured_logo.png" height="200">
</h3>

<h3 align="center">
  <p>Pre-Processing Pipeline for Nothing in Particular</p>
</h3>


The description for the pipeline repository goes here.
The API is hosted at `https://api.unstructured.io`.

### TODO list after generating repo from cookiecutter template:

- [ ] `git init`
- [ ] Update the pipeline name and description in `README.md` (this file)
- [ ] In a fresh Python environment, run `pip install pip-tools`
- [ ] Add any additional requirements you need to `requirements/base.in` and run `make pip-compile`
- [ ] Run `make install`
- [ ] Create a preprocessing pipeline notebook in pipeline-notebooks relevant to your project. A barebones sample notebook `pipeline-notebooks/pipeline-hello-world.ipynb` is provided for reference
- [ ] Generate the API with `make generate-api`
- [ ] Update `README.md` (this file) with examples of using the API and python code.
- [ ] Add tests in `test_emails`
- [ ] Delete this checklist and commit changes
- [ ] If needed, install additional dependencies in the `Dockerfile`. Note that the Dockerfile is provided for convenience and is not a hard requirement for local development. If that convenience provides little value to your audience, removal of the Dockerfile is another option.

## Developer Quick Start

* Using `pyenv` to manage virtualenv's is recommended
	* Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
		* `brew install pyenv-virtualenv`
	  * `pyenv install 3.8.15`
  * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

  * Create a virtualenv to work in and activate it, e.g. for one named `emails`:

	`pyenv  virtualenv 3.8.15 emails` <br />
	`pyenv activate emails`

* Run `make install`
* Start a local jupyter notebook server with `make run-jupyter` <br />
	**OR** <br />
	just start the fast-API locally with `make run-web-app`

#### Extracting whatever from some type of document

Give a description of making API calls using example `curl` commands, and example JSON responses.

For example:
```
curl -X 'POST' \
  'http://localhost:8000/emails/v0.0.1/hello-world' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@example.pdf' \
  -F 'some_parameter=something'  | jq -C . | less -R
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
