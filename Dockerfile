# syntax=docker/dockerfile:experimental
FROM cgr.dev/chainguard/wolfi-base:latest

# NOTE(crag): NB_USER ARG for mybinder.org compat:
#             https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIPELINE_PACKAGE
ARG PYTHON_VERSION="3.12"

# Set up environment
ENV PYTHON=python${PYTHON_VERSION}

COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /usr/local/bin/uv

USER root

RUN apk update && \
    apk add libxml2 python-3.12 python-3.12-base glib \
      mesa-gl mesa-libgallium cmake bash libmagic wget git openjpeg \
      poppler poppler-utils poppler-glib libreoffice tesseract && \
    git clone --depth 1 https://github.com/tesseract-ocr/tessdata.git /tmp/tessdata && \
    mkdir -p /usr/local/share/tessdata && \
    cp /tmp/tessdata/*.traineddata /usr/local/share/tessdata && \
    rm -rf /tmp/tessdata && \
    git clone --depth 1 https://github.com/tesseract-ocr/tessconfigs /tmp/tessconfigs && \
    cp -r /tmp/tessconfigs/configs /usr/local/share/tessdata && \
    cp -r /tmp/tessconfigs/tessconfigs /usr/local/share/tessdata && \
    rm -rf /tmp/tessconfigs && \
    apk cache clean && \
    ln -s /usr/lib/libreoffice/program/soffice.bin /usr/bin/libreoffice && \
    ln -s /usr/lib/libreoffice/program/soffice.bin /usr/bin/soffice && \
    chmod +x /usr/lib/libreoffice/program/soffice.bin && \
    apk add --no-cache font-ubuntu fontconfig && \
    fc-cache -fv && \
    ln -sf /usr/bin/$PYTHON /usr/bin/python3 && \
    addgroup --gid ${NB_UID} ${NB_USER} && \
    adduser --disabled-password --gecos "" --uid ${NB_UID} -G ${NB_USER} ${NB_USER} && \
    rm -rf /usr/lib/python3.10 && \
    rm -rf /usr/lib/python3.11 && \
    rm -rf /usr/lib/python3.13 && \
    rm -f /usr/bin/python3.13

ENV USER=${NB_USER}
ENV HOME=/home/${NB_USER}
COPY --chown=${NB_USER} scripts/initialize-libreoffice.sh ${HOME}/initialize-libreoffice.sh

USER ${NB_USER}
WORKDIR ${HOME}

# Initialize libreoffice config as non-root user (required for soffice to work properly)
# See: https://github.com/Unstructured-IO/unstructured/issues/3105
RUN ./initialize-libreoffice.sh && rm initialize-libreoffice.sh

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/${NB_USER}/.local/bin:${PATH}"
ENV TESSDATA_PREFIX=/usr/local/share/tessdata
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT="${HOME}/.local"

COPY --chown=${NB_USER}:${NB_USER} pyproject.toml pyproject.toml
COPY --chown=${NB_USER}:${NB_USER} uv.lock uv.lock
RUN uv sync --no-dev --no-install-project --frozen

ARG PANDOC_VERSION="3.9"
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then PANDOC_ARCH="amd64"; else PANDOC_ARCH="arm64"; fi && \
    wget -q "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${PANDOC_ARCH}.tar.gz" -O /tmp/pandoc.tar.gz && \
    tar -xzf /tmp/pandoc.tar.gz -C /tmp && \
    cp /tmp/pandoc-${PANDOC_VERSION}/bin/pandoc /home/${USER}/.local/bin/ && \
    rm -rf /tmp/pandoc*

RUN ${PYTHON} -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()" && \
    ${PYTHON} -c "from unstructured.partition.model_init import initialize; initialize()" && \
    ${PYTHON} -c "from unstructured_inference.models.tables import UnstructuredTableTransformerModel; model = UnstructuredTableTransformerModel(); model.initialize('microsoft/table-transformer-structure-recognition')"

COPY --chown=${NB_USER}:${NB_USER} CHANGELOG.md CHANGELOG.md
COPY --chown=${NB_USER}:${NB_USER} logger_config.yaml logger_config.yaml
COPY --chown=${NB_USER}:${NB_USER} prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY --chown=${NB_USER}:${NB_USER} exploration-notebooks exploration-notebooks
COPY --chown=${NB_USER}:${NB_USER} scripts/app-start.sh scripts/app-start.sh

ENTRYPOINT ["scripts/app-start.sh"]
# Expose a default port of 8000. Note: The EXPOSE instruction does not actually publish the port,
# but some tooling will inspect containers and perform work contingent on networking support declared.

EXPOSE 8000
