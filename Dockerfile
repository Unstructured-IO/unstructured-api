# syntax=docker/dockerfile:experimental
FROM cgr.dev/chainguard/wolfi-base:latest

# NOTE(crag): NB_USER ARG for mybinder.org compat:
#             https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIP_VERSION
ARG PIPELINE_PACKAGE
ARG PYTHON_VERSION="3.12"

# Set up environment
ENV PYTHON=python${PYTHON_VERSION}
ENV PIP="${PYTHON} -m pip"

USER root

COPY ./docker/packages/*.apk /tmp/packages/

RUN apk update && \
    apk add libxml2 python-3.12 python-3.12-base py3.12-pip glib \
      mesa-gl mesa-libgallium cmake bash libmagic wget git openjpeg \
      poppler poppler-utils poppler-glib libreoffice tesseract && \
    apk add --allow-untrusted /tmp/packages/pandoc-3.1.8-r0.apk && \
    rm -rf /tmp/packages && \
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
    apk upgrade --no-cache py3.12-pip && \
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

COPY --chown=${NB_USER}:${NB_USER} requirements/base.txt requirements-base.txt
RUN ${PIP} install pip==${PIP_VERSION} && \
    ${PIP} install --no-cache -r requirements-base.txt

RUN ${PYTHON} -c "from unstructured.nlp.tokenize import download_nltk_packages; download_nltk_packages()" && \
    ${PYTHON} -c "from unstructured.partition.model_init import initialize; initialize()"

COPY --chown=${NB_USER}:${NB_USER} CHANGELOG.md CHANGELOG.md
COPY --chown=${NB_USER}:${NB_USER} logger_config.yaml logger_config.yaml
COPY --chown=${NB_USER}:${NB_USER} prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY --chown=${NB_USER}:${NB_USER} exploration-notebooks exploration-notebooks
COPY --chown=${NB_USER}:${NB_USER} scripts/app-start.sh scripts/app-start.sh

ENTRYPOINT ["scripts/app-start.sh"]
# Expose a default port of 8000. Note: The EXPOSE instruction does not actually publish the port,
# but some tooling will inspect containers and perform work contingent on networking support declared.

EXPOSE 8000
