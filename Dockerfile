# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:wolfi-base@sha256:7c3af225a39f730f4feee705df6cd8d1570739dc130456cf589ac53347da0f1d as base

USER root

# NOTE: NB_USER ARG for mybinder.org compat:
# https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIPELINE_PACKAGE
ARG PYTHON_VERSION="3.11"

# Set up environment
ENV PYTHON=python${PYTHON_VERSION}
ENV PIP="${PYTHON} -m pip"
ENV HOME=/home/notebook-user

# Create user and home directory if user does not exist
RUN if ! id -u notebook-user > /dev/null 2>&1; then \
      adduser -u 1000 -h ${HOME} -D notebook-user; \
    fi

# Ensure the home directory exists and has the correct permissions
RUN mkdir -p ${HOME} && chown -R notebook-user:1000 ${HOME}

WORKDIR ${HOME}
USER notebook-user

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/notebook-user/.local/bin:${PATH}"

FROM base as python-deps
USER root
COPY --chown=1000:1000 requirements/base.txt requirements-base.txt
RUN ${PIP} install pip==23.2.1
RUN ${PIP} install --no-cache-dir -r requirements-base.txt
USER notebook-user

FROM python-deps as model-deps
RUN ${PYTHON} -c "import nltk; nltk.download('punkt')" && \
  ${PYTHON} -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  ${PYTHON} -c "from unstructured.partition.model_init import initialize; initialize()"

FROM model-deps as code
USER root
COPY --chown=1000:1000 CHANGELOG.md CHANGELOG.md
COPY --chown=1000:1000 logger_config.yaml logger_config.yaml
COPY --chown=1000:1000 prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY --chown=1000:1000 exploration-notebooks exploration-notebooks
COPY --chown=1000:1000 scripts/app-start.sh scripts/app-start.sh
USER notebook-user

ENTRYPOINT ["scripts/app-start.sh"]
# Expose a default port of 8000. Note: The EXPOSE instruction does not actually publish the port,
# but some tooling will inspect containers and perform work contingent on networking support declared.
EXPOSE 8000
