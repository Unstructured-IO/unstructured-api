# syntax=docker/dockerfile:experimental
FROM quay.io/unstructured-io/base-images:rocky8.7

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
RUN useradd --uid ${NB_UID}  --gid ${NB_UID} ${NB_USER}
WORKDIR ${HOME}
RUN mkdir ${HOME}/.ssh && chmod go-rwx ${HOME}/.ssh \
  &&  ssh-keyscan -t rsa github.com >> /home/${NB_USER}/.ssh/known_hosts

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/${NB_USER}/.local/bin:${PATH}"

RUN dnf install -y libreoffice-writer libreoffice-impress libreoffice-draw libreoffice-math libreoffice-core

# COPY requirements/dev.txt requirements-dev.txt
COPY requirements/base.txt requirements-base.txt
RUN python3.8 -m pip install pip==${PIP_VERSION} \
  && dnf -y groupinstall "Development Tools" \
  && su -l ${NB_USER} -c 'pip3.8 install  --no-cache  -r requirements-base.txt' \
  # required for detectron2 install on Mac M1
  && su -l ${NB_USER} -c  'pip3.8 install --no-cache tensorboard>=2.12.2' \
  && su -l ${NB_USER} -c 'pip3.8 install --no-cache "detectron2@git+https://github.com/facebookresearch/detectron2.git@e2ce8dc#egg=detectron2"' \
  && dnf -y groupremove "Development Tools" \
  && ln -s /home/notebook-user/.local/bin/pip /usr/local/bin/pip || true

USER ${NB_USER}

RUN python3.8 -c "import nltk; nltk.download('punkt')" && \
  python3.8 -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  python3.8 -c "from unstructured.ingest.doc_processor.generalized import initialize; initialize()"

USER ${NB_USER}

COPY --chown=${NB_USER}:${NB_USER} CHANGELOG.md CHANGELOG.md
COPY --chown=${NB_USER}:${NB_USER} logger_config.yaml logger_config.yaml
COPY --chown=${NB_USER}:${NB_USER} prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY --chown=${NB_USER}:${NB_USER} exploration-notebooks exploration-notebooks
COPY --chown=${NB_USER}:${NB_USER} pipeline-notebooks pipeline-notebooks

ENTRYPOINT ["uvicorn", "prepline_general.api.app:app", \
  "--log-config", "logger_config.yaml", \
  "--host", "0.0.0.0"]
