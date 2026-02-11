PIPELINE_FAMILY := general
PIPELINE_PACKAGE := general
PACKAGE_NAME := prepline_${PIPELINE_PACKAGE}

.PHONY: help
help: Makefile
	@sed -n 's/^\(## \)\([a-zA-Z]\)/\2/p' $<


###########
# Install #
###########

## install-base:                installs minimum requirements to run the API
.PHONY: install-base
install-base: install-base-packages install-nltk-models

## install:                     installs all test and dev requirements
.PHONY: install
install: install-base install-test

.PHONY: install-base-packages
install-base-packages:
	uv sync --no-dev --frozen

.PHONY: install-test
install-test:
	uv sync --group test --frozen

.PHONY: install-nltk-models
install-nltk-models:
	uv run python -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()"

## lock:                        regenerates uv.lock
.PHONY: lock
lock:
	uv lock --upgrade

PANDOC_VERSION := 3.9
.PHONY: install-pandoc
install-pandoc:
	@ARCH=$$(uname -m) && \
	if [ "$$ARCH" = "x86_64" ]; then PANDOC_ARCH="amd64"; else PANDOC_ARCH="arm64"; fi && \
	wget -q "https://github.com/jgm/pandoc/releases/download/$(PANDOC_VERSION)/pandoc-$(PANDOC_VERSION)-linux-$$PANDOC_ARCH.tar.gz" -O /tmp/pandoc.tar.gz && \
	tar -xzf /tmp/pandoc.tar.gz -C /tmp && \
	sudo cp /tmp/pandoc-$(PANDOC_VERSION)/bin/pandoc /usr/local/bin/ && \
	rm -rf /tmp/pandoc*

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
	PIPELINE_FAMILY=${PIPELINE_FAMILY} PIPELINE_PACKAGE=${PIPELINE_PACKAGE} ./scripts/docker-build.sh

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
	PYTHONPATH=$(realpath .) uv run uvicorn ${PACKAGE_NAME}.api.app:app --reload --log-config logger_config.yaml

#################
# Test and Lint #
#################

## test:                        runs core tests
.PHONY: test
test:
	PYTHONPATH=. uv run pytest -n auto -v test_${PIPELINE_PACKAGE} --cov=${PACKAGE_NAME} --cov-report term-missing

# Setting a low bar here - need more tests!
.PHONY: check-coverage
check-coverage:
	uv run coverage report --fail-under=60

## check:                       runs linters (includes tests)
.PHONY: check
check: check-src check-tests check-version

## check-src:                   runs linters (source only, no tests)
.PHONY: check-src
check-src:
	uv run --no-sync ruff format --check ${PACKAGE_NAME}
	uv run --no-sync ruff check ${PACKAGE_NAME}
	uv run --no-sync mypy ${PACKAGE_NAME} --ignore-missing-imports --implicit-optional

.PHONY: check-tests
check-tests:
	uv run --no-sync ruff format --check test_${PIPELINE_PACKAGE} scripts/smoketest.py
	uv run --no-sync ruff check test_${PIPELINE_PACKAGE} scripts/smoketest.py

## tidy:                        run ruff format and fix
.PHONY: tidy
tidy:
	uv run --no-sync ruff format ${PACKAGE_NAME} test_${PIPELINE_PACKAGE} scripts/smoketest.py
	uv run --no-sync ruff check --fix ${PACKAGE_NAME} test_${PIPELINE_PACKAGE} scripts/smoketest.py

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
		-f prepline_general/api/__version__.py release \

## version-sync:                update references to version with most recent version from CHANGELOG.md
.PHONY: version-sync
version-sync:
	scripts/version-sync.sh \
		-s CHANGELOG.md \
		-f prepline_general/api/__version__.py release \
