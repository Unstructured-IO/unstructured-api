## 0.0.24

* Add support for `ocr_only` strategy and `ocr_languages` parameter
* Remove building `detectron2` from source in Dockerfile

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
