# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:rocky9.2-8@sha256:68b11677eab35ea702cfa682202ddae33f2053ea16c14c951120781a2dcac1b2 as base

# NOTE(crag): NB_USER ARG for mybinder.org compat:
#             https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIP_VERSION
ARG PIPELINE_PACKAGE

# Set up environment
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}

RUN groupadd --gid ${NB_UID} ${NB_USER}
RUN useradd --uid ${NB_UID} --gid ${NB_UID} ${NB_USER}
WORKDIR ${HOME}

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/${NB_USER}/.local/bin:${PATH}"

FROM base as python-deps
# COPY requirements/dev.txt requirements-dev.txt
COPY requirements/base.txt requirements-base.txt
RUN python3.10 -m pip install pip==${PIP_VERSION} \
  && dnf -y groupinstall "Development Tools" \
  && su -l ${NB_USER} -c 'pip3.10 install  --no-cache  -r requirements-base.txt' \
  && dnf -y groupremove "Development Tools" \
  && dnf clean all \
  && ln -s /home/notebook-user/.local/bin/pip3.10 /usr/local/bin/pip3.10 || true

USER ${NB_USER}

FROM python-deps as model-deps
# Note(yuming): quick workaround for ingest import error
# should import initialize within unstructured but out of ingest dir
COPY --chown=${NB_USER}:${NB_USER} scripts/hi_res_model_initialize.py  hi_res_model_initialize.py 
RUN python3.10 -c "import nltk; nltk.download('punkt')" && \
  python3.10 -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  python3.10 -c "from hi_res_model_initialize import initialize; initialize()"

FROM model-deps as code
COPY --chown=${NB_USER}:${NB_USER} CHANGELOG.md CHANGELOG.md
COPY --chown=${NB_USER}:${NB_USER} logger_config.yaml logger_config.yaml
COPY --chown=${NB_USER}:${NB_USER} prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY --chown=${NB_USER}:${NB_USER} exploration-notebooks exploration-notebooks
COPY --chown=${NB_USER}:${NB_USER} scripts/app-start.sh scripts/app-start.sh

ENTRYPOINT ["scripts/app-start.sh"]
# Expose a default port of 8000. Note: The EXPOSE instruction does not actually publish the port,
# but some tooling will inspect containers and perform work contingent on networking support declared.
EXPOSE 8000