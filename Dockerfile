# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:wolfi-base@sha256:7c3af225a39f730f4feee705df6cd8d1570739dc130456cf589ac53347da0f1d as base

USER root

# Set up environment
ENV PYTHON=python3.11
ENV PIP="${PYTHON} -m pip"
ENV HOME=/root
ENV PIPELINE_PACKAGE=general

WORKDIR ${HOME}

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="${HOME}/.local/bin:${PATH}"

FROM base as python-deps
COPY requirements/base.txt requirements-base.txt
RUN ${PIP} install pip==23.2.1
RUN ${PIP} install --no-cache-dir -r requirements-base.txt

FROM python-deps as model-deps
RUN ${PYTHON} -c "import nltk; nltk.download('punkt')" && \
  ${PYTHON} -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  ${PYTHON} -c "from unstructured.partition.model_init import initialize; initialize()"

FROM model-deps as code
COPY CHANGELOG.md CHANGELOG.md
COPY logger_config.yaml logger_config.yaml
COPY prepline_general/ prepline_general/
COPY exploration-notebooks exploration-notebooks
COPY scripts/app-start.sh scripts/app-start.sh

ENTRYPOINT ["scripts/app-start.sh"]
# Expose a default port of 8000. Note: The EXPOSE instruction does not actually publish the port,
# but some tooling will inspect containers and perform work contingent on networking support declared.
EXPOSE 8000