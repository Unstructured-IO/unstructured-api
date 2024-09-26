# syntax=docker/dockerfile:experimental
FROM harbor.sionic.tech/unstructured/c212ca88@sha256:c212ca88005631cb80854341e741451d63967c5f95c4d477963b57b732492738
USER root

# Set up environment
ENV PYTHON=python3.11
ENV PIP="${PYTHON} -m pip"
ENV HOME=/root
ENV PIPELINE_PACKAGE=general
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PATH="${HOME}/.local/bin:${PATH}"
WORKDIR ${HOME}

# Install LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements/base.txt requirements-base.txt
RUN ${PIP} install pip==23.2.1
RUN ${PIP} install --no-cache-dir -r requirements-base.txt

# Create a directory for the unstructured package
RUN mkdir -p /app/unstructured

# Create symbolic link for unstructured if necessary
RUN if [ ! -d "$(${PYTHON} -c "import site; print(site.getsitepackages()[0])")/unstructured" ]; then \
        ln -s /app/unstructured $(${PYTHON} -c "import site; print(site.getsitepackages()[0])")/unstructured; \
    fi

# Reset Python environment
RUN ${PYTHON} -m site

# Ensure numpy is installed (in case it's not in the base image or requirements)
RUN ${PIP} install numpy

# Debug information
RUN echo "PYTHONPATH: $PYTHONPATH" && \
    ${PYTHON} -c "import sys; print('Python sys.path:', sys.path)" && \
    ls -l /app && \
    ${PYTHON} --version && \
    ${PYTHON} -c "import site; print(site.getsitepackages())" && \
    ${PYTHON} -c "import unstructured; print(unstructured.__file__)" || echo "Failed to import unstructured" && \
    ${PYTHON} -c "import numpy; print(numpy.__version__)" || echo "Failed to import numpy" && \
    which soffice && soffice --version || echo "Failed to find or run soffice"

# Download NLTK data and initialize unstructured
RUN ${PYTHON} -c "import nltk; nltk.download('punkt')" && \
    ${PYTHON} -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
    ${PYTHON} -c "from unstructured.partition.model_init import initialize; initialize()"

# Copy application files
COPY logger_config.yaml logger_config.yaml
COPY prepline_general/ prepline_general/
COPY scripts/app-start.sh scripts/app-start.sh

ENTRYPOINT ["scripts/app-start.sh"]

# Expose a default port of 8000
EXPOSE 8000