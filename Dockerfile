# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:wolfi-base@sha256:7c3af225a39f730f4feee705df6cd8d1570739dc130456cf589ac53347da0f1d as base

USER root

# NOTE: NB_USER ARG for mybinder.org compat:
# https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIP_VERSION
ARG PIPELINE_PACKAGE
ARG PYTHON_VERSION="3.11"

# Set up environment
ENV PYTHON=python${PYTHON_VERSION}
ENV PIP="${PYTHON} -m pip"
ENV HOME=/home/${NB_USER}

# Create user and home directory if user does not exist
RUN if ! id -u ${NB_USER} > /dev/null 2>&1; then \
      adduser -u ${NB_UID} -h ${HOME} -D ${NB_USER}; \
    fi

WORKDIR ${HOME}
USER ${NB_USER}

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/${NB_USER}/.local/bin:${PATH}"

FROM base as python-deps
COPY requirements/base.txt requirements-base.txt
RUN ${PIP} install pip==${PIP_VERSION}
RUN ${PIP} install --no-cache-dir -r requirements-base.txt

# Uncomment this section if model dependencies are needed
# FROM python-deps as model-deps
# RUN ${PYTHON} -c "import nltk; nltk.download('punkt')" && \
#   ${PYTHON} -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
#   ${PYTHON} -c "from unstructured.partition.model_init import initialize; initialize()"

FROM python-deps as code
COPY CHANGELOG.md CHANGELOG.md
COPY logger_config.yaml logger_config.yaml
COPY prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY exploration-notebooks exploration-notebooks
COPY scripts/app-start.sh scripts/app-start.sh

ENTRYPOINT ["scripts/app-start.sh"]
# Expose a default port of 8000. Note: The EXPOSE instruction does not actually publish the port,
# but some tooling will inspect containers and perform work contingent on networking support declared.
EXPOSE 8000
