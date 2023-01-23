PIPELINE_FAMILY := emails
PIPELINE_PACKAGE := emails
PACKAGE_NAME := prepline_${PIPELINE_PACKAGE}
PIP_VERSION := 22.1.2

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install-base:                installs minimum requirements to run the API
.PHONY: install-base
install-base: install-base-pip-packages

## install:                     installs all test and dev requirements
.PHONY: install
install: install-base install-test install-dev

.PHONY: install-base-pip-packages
install-base-pip-packages:
	python3 -m pip install pip==${PIP_VERSION}
	pip install -r requirements/base.txt

.PHONY: install-test
install-test:
	pip install -r requirements/test.txt

.PHONY: install-dev
install-dev:
	pip install -r requirements/dev.txt

.PHONY: install-ci
install-ci: install-base install-test

.PHONE: install-nltk
install-nltk:
	python -c "import nltk; nltk.download('punkt')"

## pip-compile:                 compiles all base/dev/test requirements
.PHONY: pip-compile
pip-compile:
	pip-compile requirements/base.in
	pip-compile requirements/dev.in
	pip-compile requirements/test.in


#########
# Build #
#########

## generate-api:                generates the FastAPI python APIs from notebooks
.PHONY: generate-api
generate-api:
	PYTHONPATH=. unstructured_api_tools convert-pipeline-notebooks \
		--input-directory ./pipeline-notebooks \
		--output-directory ./${PACKAGE_NAME}/api


##########
# Docker #
##########

# Docker targets are provided for convenience only and are not required in a standard development environment

# Note that the image has notebooks baked in, however the current working directory
# is mounted under /home/notebook-user/local/ when the image is started with
# docker-start-api or docker-start-jupyter

.PHONY: docker-build
docker-build:
	PIP_VERSION=${PIP_VERSION} PIPELINE_FAMILY=${PIPELINE_FAMILY} PIPELINE_PACKAGE=${PIPELINE_PACKAGE} ./scripts/docker-build.sh

.PHONY: docker-start-api
docker-start-api:
	docker run -p 8000:8000 --mount type=bind,source=$(realpath .),target=/home/notebook-user/local -t --rm pipeline-family-${PIPELINE_FAMILY}-dev:latest uvicorn ${PACKAGE_NAME}.api.app:app --host 0.0.0.0 --port 8000

.PHONY: docker-start-jupyter
docker-start-jupyter:
	docker run -p 8888:8888 --mount type=bind,source=$(realpath .),target=/home/notebook-user/local -t --rm pipeline-family-${PIPELINE_FAMILY}-dev:latest jupyter-notebook --port 8888 --ip 0.0.0.0 --no-browser --NotebookApp.token='' --NotebookApp.password=''


#########
# Local #
#########

## run-jupyter:                 starts jupyter notebook
.PHONY: run-jupyter
run-jupyter:
	PYTHONPATH=$(realpath .) JUPYTER_PATH=$(realpath .) jupyter-notebook --NotebookApp.token='' --NotebookApp.password=''

## run-web-app:                 runs the FastAPI api with hot reloading
.PHONY: run-web-app
run-web-app:
	 PYTHONPATH=$(realpath .) uvicorn ${PACKAGE_NAME}.api.app:app --reload

#################
# Test and Lint #
#################

## test:                        runs core tests
.PHONY: test
test:
	PYTHONPATH=. pytest test_${PIPELINE_PACKAGE} --cov=${PACKAGE_NAME} --cov-report term-missing

.PHONY: check-coverage
check-coverage:
	coverage report --fail-under=90

## test-integration:            runs integration tests
.PHONY: test-integration
test-integration:
	PYTHONPATH=. pytest test_${PIPELINE_PACKAGE}_integration

## api-check:                   verifies auto-generated pipeline APIs match the existing ones
.PHONY: api-check
api-check:
	PYTHONPATH=. PACKAGE_NAME=${PACKAGE_NAME} ./scripts/test-doc-pipeline-apis-consistent.sh

## check:                       runs linters (includes tests)
.PHONY: check
check: check-src check-tests check-version

## check-src:                   runs linters (source only, no tests)
.PHONY: check-src
check-src:
	black --line-length 100 ${PACKAGE_NAME} --check --exclude ${PACKAGE_NAME}/api
	flake8 ${PACKAGE_NAME}
	mypy ${PACKAGE_NAME} --ignore-missing-imports --install-types --non-interactive --implicit-optional

.PHONY: check-tests
check-tests:
	black --line-length 100 test_${PIPELINE_PACKAGE} --check
	flake8 test_${PIPELINE_PACKAGE}

## tidy:                        run black
.PHONY: tidy
tidy:
	black --line-length 100 ${PACKAGE_NAME}
	black --line-length 100 test_${PIPELINE_PACKAGE}

## check-scripts:               run shellcheck
.PHONY: check-scripts
check-scripts:
    # Fail if any of these files have warnings
	scripts/shellcheck.sh

## check-version:               run check to ensure version in CHANGELOG.md matches references in files
.PHONY: check-version
check-version:
# Fail if syncing version would produce changes
	scripts/version-sync.sh -c \
		-s CHANGELOG.md \
		-f README.md api-release \
		-f preprocessing-pipeline-family.yaml release

## check-notebooks:             check that executing and cleaning notebooks doesn't produce changes
.PHONY: check-notebooks
check-notebooks:
	scripts/check-and-format-notebooks.py --check

## tidy-notebooks:	             execute notebooks and remove metadata
.PHONY: tidy-notebooks
tidy-notebooks:
	scripts/check-and-format-notebooks.py

## version-sync:                update references to version with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-s CHANGELOG.md \
		-f README.md api-release \
		-f preprocessing-pipeline-family.yaml release \
