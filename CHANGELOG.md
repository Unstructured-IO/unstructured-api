## 0.0.73

* Bump to `unstructured` 0.14.10

## 0.0.72

* Fix certain filetypes failing mimetype lookup in the new base image

## 0.0.71

* replace rockylinux with chainguard/wolfi as a base image for `amd64`

## 0.0.70

* Bump to `unstructured` 0.14.6
* Bump to `unstructured-inference` 0.7.35

## 0.0.69

* Bump to `unstructured` 0.14.4
* Add handling for `pdf_infer_table_structure` to reflect the "tables off by default" behavior in `unstructured`.

## 0.0.68

* Fix list params such as `extract_image_block_types` not working via the python/js clients

## 0.0.67

* Allow for a different server port with the PORT variable
* Change pdf_infer_table_structure parameter from being disabled in auto strategy.

## 0.0.66

* Add support for `unique_element_ids` parameter.
* Add max lifetime, via MAX_LIFETIME_SECONDS env-var, to API containers
* Bump unstructured to 0.13.5
* Change default values for `pdf_infer_table_structure` and `skip_infer_table_types`. Mark `pdf_infer_table_structure` deprecated.
* Add support for the `starting_page_number` param.

## 0.0.65

* Bump unstructured to 0.12.4
* Add support for both `list[str]` and `str` input formats for `ocr_languages` parameter
* Adds support for additional MIME types from `unstructured`
* Document the support for gzip files and add additional testing

## 0.0.64

* Bump Pydantic to 2.5.x and remove it from explicit dependencies list (will be managed by fastapi)
* Introduce Form params description in the code, which will form openapi and swagger documentation
* Roll back some openapi customizations
* Keep backward compatibility for passing parameters in form of `list[str]` (will not be shown in the documentation)

## 0.0.63

* Bump unstructured to 0.12.2
* Fix bug that ignored `combine_under_n_chars` chunking option argument.

## 0.0.62

* Add hi_res_model_name to partition and deprecate model_name
* Bump unstructured to 0.12.0
* Add support for returning extracted image blocks as base64 encoded data stored in metadata fields

## 0.0.61

* Bump unstructured to 0.11.6
* Handle invalid hi_res_model_name kwarg

## 0.0.60

* Enable self-hosted authorization using UNSTRUCTURED_API_KEY env variable

## 0.0.59

* Bump unstructured to 0.11.0

## 0.0.58

* Bump unstructured to 0.10.30

## 0.0.57
* Make sure `multipage_sections` param defaults to `true` as per the readme
* Bump unstructured to 0.10.29


## 0.0.56
* **Add `max_characters` param for chunking** This param gives users additional control to "chunk" elements into larger or smaller `CompositeElement`s
* Bump unstructured to 0.10.28
* Make sure chipperv2 is called whien `hi_res_model_name==chipper`


## 0.0.55

* Bump unstructured to 0.10.26
* Bring parent_id metadata field back after fixing a backwards compatibility bug
* Restrict Chipper usage to one at a time. The model is very resource intense, and this will prevent issues while we improve it.

## 0.0.54

* Bump unstructured to 0.10.25
* Use a generator when splitting pdfs in parallel mode
* Add a default memory minimum for 503 check
* Fix an UnboundLocalError when an invalid docx file is caught

## 0.0.53

* Bump unstructured to 0.10.23
* Simplify the error message for BadZipFile errors

## 0.0.52

* Bump unstructured to 0.10.21
* Fix an unhandled error when a non pdf file is sent with content-type pdf
* Fix an unhandled error when a non docx file is sent with content-type docx
* Fix an unhandled error when a non-Unstructured json schema is sent

## 0.0.51

* Bump unstructured to 0.10.19

## 0.0.50

* Bump unstructured to 0.10.18

## 0.0.49

* Remove spurious whitespace in `app-start.sh`. **This fixes deployments in some envs such as Google Cloud Run**.

## 0.0.48

* **Adds `languages` kwarg** `ocr_languages` will eventually be deprecated and replaced by `lanugages` to specify what languages to use for OCR
* Adds a startup log and other minor cleanups

## 0.0.47

* **Adds `chunking_strategy` kwarg and associated params** These params allow users to "chunk" elements into larger or smaller `CompositeElement`s
* **Remove `parent_id` from the element metadata**. New metadata fields are causing errors with existing installs. We'll readd this once a fix is widely available.
* **Fix some pdfs incorrectly returning a file is encrypted error**. The `pypdf.is_encrypted` check caused us to return this error even if the file is readable.

## 0.0.46

* Bump unstructured to 0.10.16

## 0.0.45

* Drop `detection_class_prob` from the element metadata. This broke backwards compatibility when library users called `partition_via_api`.
* Bump unstructured to 0.10.15

## 0.0.44

* Bump unstructured to 0.10.14
* Improve parallel mode retry handling
* Improve logging during error handling. We don't need to log stack traces for expected errors.

## 0.0.43

* Bump unstructured to 0.10.13
* Bump unstructured-inference to 0.5.25
* Remove dependency on unstructured-api-tools
* Add a top level error handler for more consistent response bodies
* Tesseract minor version bump to 5.3.2

## 0.0.42

* Update readme for parameter `hi_res_model_name`
* Fix a bug using `hi_res_model_name` in parallel mode
* Bump unstructured library to 0.10.12
* Bump unstructured-inference to 0.5.22

## 0.0.41

* Bump unstructured library to 0.10.8
* Bump unstructured-inference to 0.5.17

## 0.0.40

* Reject traffic when overloaded via `UNSTRUCTURED_MEMORY_FREE_MINIMUM_MB`
* Docker image built with Python 3.10 rather than 3.8

## 0.0.39

* Fix wrong handleing on param skip_infer_table_types
* Pin `safetensors` to fix a build error with 0.0.38

## 0.0.38

* Fix page break has None page number bug
* Bump unstructured to 0.10.5
* Bump unstructured-ingest to 0.5.15
* Fix UnboundLocalError using pdfs in parallel mode

## 0.0.37

* Bump unstructured to 0.10.4

## 0.0.36

* Fix a bug in parallel mode causing `not a valid pdf` errors
* Bump unstructured to 0.10.2, unstructured-inference to 0.5.13

## 0.0.35

* Bump unstructured library to 0.9.2
* Fix a misleading error in make docker-test

## 0.0.34

* Bump unstructured library to 0.9.0
* Add table support for image with parameter `skip_infer_table_types`
* Add support for gzipped files

## 0.0.33

* Image tweak, move application entrypoint to scripts/app-start.sh

## 0.0.32

* Throw 400 error if a PDF is password protected
* Improve logging of params to single line json
* Add support for `include_page_breaks` parameter

## 0.0.31

* Support model name as api parameter
* Add retry parameters on fanout requests
* Bump unstructured library to 0.8.1
* Fix how to remove an element's coordinate information

## 0.0.30

* Add table extraction support for hi_res strategy
* Add support for `encoding` parameter
* Add support for `xml_keep_tags` parameter
* Add env variables for additional parallel mode tweaking

## 0.0.29

* Support .msg files
* Refactor parallel mode and add smoke test
* Fix header value for api key

## 0.0.28

* Bump unstructured library to 0.7.8 for bug fixes

## 0.0.27

* Update documentation and tests for filetypes to sync with partition.auto
* Add support for .rst, .tsv, .xml
* Move PYPDF2 to pypdf since PYPDF2 is deprecated

## 0.0.26

* Add support for `ocr_only` strategy and `ocr_languages` parameter
* Remove building `detectron2` from source in Dockerfile
* Convert strategy from fast to auto for images since there is no fast strategy for images

## 0.0.25

* Bump image to use python 3.8.17 instead of 3.8.15

## 0.0.24

* Add returning text/csv to pipeline_api

## 0.0.23

* Add support for csv files

## 0.0.22

* Add parallel processing mode for pages within a pdf

## 0.0.21

* Bump version of base image to use new stable version of tesseract
* Bump to unstructured==0.7.1 for various bug fixes.

## 0.0.20

* Supports additional filetypes: epub, odt, rft

## 0.0.19

* Updating data type of optional os env var `ALLOWED_ORIGINS`

## 0.0.18

* Add optional CORS to api if os env var `ALLOWED_ORIGINS` is set

## 0.0.17

* Add config for unstructured.trace logger

## 0.0.16

* Fix image build steps to support detectron2 install from Mac M1/M2
* Upgrade to openssl 1.1.1 to accomodate the latest urllib3
* Bump unstructured for SpooledTemporaryFile fix

## 0.0.15

* Add msg and json types to supported

## 0.0.14

* Bump unstructured to the latest version

## 0.0.13

* Posting a bad .pdf results in a 400

## 0.0.12

* Remove coordinates field from response elements by default

## 0.0.11

* Add caching from the registry for `make docker-build`
* Add fix for empty content type error

## 0.0.10

* Bump unstructured-api-tools for better 'file type not supported' response messages

## 0.0.9

* Updated detectron version
* Update docker-build to use the public registry as a cache
* Adds a strategy parameter to pipeline_api
* Passing file, file_filename, and content_type to `partition`

## 0.0.8

* Sensible logging config

## 0.0.7

* Minor version bump

## 0.0.6

* Minor version bump

## 0.0.5

* Updated Dockerfile for public release
* Remove rate limiting in the API
* Add file type validation via UNSTRUCTURED_ALLOWED_MIMETYPES
* Major semver route also supported: /general/v0/general

## 0.0.4

* Changed pipeline name to `pipeline-general`
* Changed pipeline to handle a variety of documents not just emails
* Update Dockerfile, all supported library files.
* Add sample-docs for pdf and pdf image.

## 0.0.3

* Add emails pipeline Dockerfile

## 0.0.2

* Add pipeline notebook

## 0.0.1

* Initial pipeline setup
