PIPELINE_FAMILY := general
PIPELINE_PACKAGE := general
PACKAGE_NAME := prepline_${PIPELINE_PACKAGE}
PIP_VERSION := 23.2.1
ARCH := $(shell uname -m)

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install-base:                installs minimum requirements to run the API
.PHONY: install-base
install-base: install-base-pip-packages install-nltk-models

## install:                     installs all test and dev requirements
.PHONY: install
install:install-base install-test

.PHONY: install-base-pip-packages
install-base-pip-packages:
	python3 -m pip install pip==${PIP_VERSION}
	python3 -m pip install -r requirements/base.txt

.PHONY: install-test
install-test: install-base
	python3 -m pip install -r requirements/test.txt

.PHONY: install-ci
install-ci: install-test

.PHONE: install-nltk-models
install-nltk-models:
	python3 -c "import nltk; nltk.download('punkt')"
	python3 -c "import nltk; nltk.download('averaged_perceptron_tagger')"

## pip-compile:                 compiles all base/dev/test requirements
.PHONY: pip-compile
pip-compile:
	pip-compile --upgrade requirements/base.in
	pip-compile --upgrade -o requirements/test.txt requirements/base.txt requirements/test.in

.PHONY: install-pandoc
install-pandoc:
	ARCH=${ARCH} ./scripts/install-pandoc.sh

##########
# Docker #
##########

# Docker targets are provided for convenience only and are not required in a standard development environment

# Note that the image has notebooks baked in, however the current working directory
# is mounted under /home/notebook-user/local/ when the image is started with
# docker-start-api or docker-start-jupyter

DOCKER_IMAGE ?= pipeline-family-${PIPELINE_FAMILY}-dev:latest

.PHONY: docker-build
docker-build:
	PIP_VERSION=${PIP_VERSION} PIPELINE_FAMILY=${PIPELINE_FAMILY} PIPELINE_PACKAGE=${PIPELINE_PACKAGE} ./scripts/docker-build.sh

.PHONY: docker-start-api
docker-start-api:
	docker run -p 8000:8000 \
	-it --rm  \
	--mount type=bind,source=$(realpath .),target=/home/notebook-user/local \
	$(if $(MAX_LIFETIME_SECONDS),-e MAX_LIFETIME_SECONDS=$(MAX_LIFETIME_SECONDS)) \
	pipeline-family-${PIPELINE_FAMILY}-dev:latest scripts/app-start.sh

.PHONY: docker-start-bash
docker-start-bash:
	docker run -p 8000:8000 -it --rm --mount type=bind,source=$(realpath .),target=/home/notebook-user/local --entrypoint /bin/bash pipeline-family-${PIPELINE_FAMILY}-dev:latest

.PHONY: docker-test
docker-test:
	DOCKER_IMAGE=${DOCKER_IMAGE} ./scripts/docker-smoke-test.sh

#########
# Local #
#########

## run-web-app:                 runs the FastAPI api with hot reloading
.PHONY: run-web-app
run-web-app:
	PYTHONPATH=$(realpath .) uvicorn ${PACKAGE_NAME}.api.app:app --reload --log-config logger_config.yaml

#################
# Test and Lint #
#################

## test:                        runs core tests
.PHONY: test
test:
	PYTHONPATH=. pytest -v test_${PIPELINE_PACKAGE} --cov=${PACKAGE_NAME} --cov-report term-missing

# Setting a low bar here - need more tests!
.PHONY: check-coverage
check-coverage:
	coverage report --fail-under=60

## check:                       runs linters (includes tests)
.PHONY: check
check: check-src check-tests check-version

## check-src:                   runs linters (source only, no tests)
.PHONY: check-src
check-src:
	black --line-length 100 ${PACKAGE_NAME} --check
	flake8 ${PACKAGE_NAME}
	mypy ${PACKAGE_NAME} --ignore-missing-imports --install-types --non-interactive --implicit-optional

.PHONY: check-tests
check-tests:
	black --line-length 100 test_${PIPELINE_PACKAGE} --check
	flake8 test_${PIPELINE_PACKAGE} scripts/smoketest.py

## tidy:                        run black
.PHONY: tidy
tidy:
	black --line-length 100 ${PACKAGE_NAME}
	black --line-length 100 test_${PIPELINE_PACKAGE} scripts/smoketest.py

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
		-f preprocessing-pipeline-family.yaml release \
		-f ${PACKAGE_NAME}/api/app.py release \
		-f ${PACKAGE_NAME}/api/general.py release

## version-sync:                update references to version with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-s CHANGELOG.md \
		-f preprocessing-pipeline-family.yaml release \
		-f ${PACKAGE_NAME}/api/app.py release \
		-f ${PACKAGE_NAME}/api/general.py release
