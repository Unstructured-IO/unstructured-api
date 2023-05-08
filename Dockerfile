# syntax=docker/dockerfile:experimental

FROM centos:centos7.9.2009

# NOTE(crag): NB_USER ARG for mybinder.org compat:
#             https://mybinder.readthedocs.io/en/latest/tutorials/dockerfile.html
ARG NB_USER=notebook-user
ARG NB_UID=1000
ARG PIP_VERSION
ARG PIPELINE_PACKAGE

# Install dependency packages
RUN yum -y update && \
  yum -y install poppler-utils xz-devel wget tar curl make which mailcap && \
  yum install -y epel-release && \
  yum -y install libreoffice && \
  yum clean all

# Install gcc & g++ ≥ 8 for Tesseract and Detectron2
RUN yum -y install centos-release-scl && \
  yum -y install devtoolset-9-gcc* && \
  yum clean all
SHELL [ "/usr/bin/scl", "enable", "devtoolset-9"]

# Install Tessaract
RUN set -ex && \
    $sudo yum install -y opencv opencv-devel opencv-python perl-core clang libpng-devel libtiff-devel libwebp-devel libjpeg-turbo-devel git-core libtool pkgconfig xz && \
    wget https://github.com/DanBloomberg/leptonica/releases/download/1.75.1/leptonica-1.75.1.tar.gz && \
    tar -xzvf leptonica-1.75.1.tar.gz && \
    cd leptonica-1.75.1 || exit && \
    ./configure && make && $sudo make install && \
    cd .. && \
    wget http://mirror.squ.edu.om/gnu/autoconf-archive/autoconf-archive-2017.09.28.tar.xz && \
    tar -xvf autoconf-archive-2017.09.28.tar.xz && \
    cd autoconf-archive-2017.09.28 || exit && \
    ./configure && make && $sudo make install && \
    $sudo cp m4/* /usr/share/aclocal && \
    cd .. && \
    git clone --depth 1  https://github.com/tesseract-ocr/tesseract.git tesseract-ocr && \
    cd tesseract-ocr || exit && \
    export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig && \
    scl enable devtoolset-9 -- sh -c './autogen.sh && ./configure && make && make install' && \
    cd .. && \
    git clone https://github.com/tesseract-ocr/tessdata.git  && \
    $sudo cp tessdata/*.traineddata /usr/local/share/tessdata && \
    $sudo rm -rf /tesseract-ocr /tessdata /autoconf-archive-2017.09.28* /leptonica-1.75.1* && \
    $sudo yum -y remove opencv opencv-devel opencv-python perl-core clang libpng-devel libtiff-devel libwebp-devel libjpeg-turbo-devel git-core libtool && \
    $sudo rm -rf /var/cache/yum/* && \
    $sudo rm -rf /tmp/* && \
    yum clean all

# SSL dependency gets baked into Python binary so do this first
RUN yum -y update && \
  yum install -y perl-core pcre-devel && \
  wget https://ftp.openssl.org/source/openssl-1.1.1k.tar.gz && \
  tar -xzvf openssl-1.1.1k.tar.gz && \
  cd openssl-1.1.1k && \
  ./config shared --prefix=/usr/local/ssl --openssldir=/usr/local/ssl && \
  make && \
  make install && cd .. && \
  ldconfig && \
  rm -rf openssl-1.1.1k && rm openssl-1.1.1k.tar.gz && \
  $sudo yum -y remove perl-core pcre-devel && \
  yum clean all

ENV PATH="/usr/local/ssl/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/ssl/lib:$LD_LIBRARY_PATH"
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt

# Install Python
RUN yum -y install bzip2-devel libffi-devel make git sqlite-devel && \
  curl -O https://www.python.org/ftp/python/3.8.15/Python-3.8.15.tgz && tar -xzf Python-3.8.15.tgz && \
  cd Python-3.8.15/ && \
  ./configure --enable-optimizations --with-openssl=/usr/local/ssl && \
  make altinstall && \
  cd .. && rm -rf Python-3.8.15* && \
  ln -s /usr/local/bin/python3.8 /usr/local/bin/python3 && \
  $sudo yum -y remove bzip2-devel libffi-devel make sqlite-devel && \
  $sudo rm -rf /var/cache/yum/* && \
  yum clean all

# Set up environment
ENV USER ${NB_USER}
ENV HOME /home/${NB_USER}

RUN groupadd --gid ${NB_UID} ${NB_USER}
RUN useradd --uid ${NB_UID}  --gid ${NB_UID} ${NB_USER}
USER ${NB_USER}
WORKDIR ${HOME}
RUN mkdir ${HOME}/.ssh && chmod go-rwx ${HOME}/.ssh \
  &&  ssh-keyscan -t rsa github.com >> /home/${NB_USER}/.ssh/known_hosts

ENV PYTHONPATH="${PYTHONPATH}:${HOME}"
ENV PATH="/home/${NB_USER}/.local/bin:${PATH}"

# COPY requirements/dev.txt requirements-dev.txt
COPY requirements/base.txt requirements-base.txt
RUN python3.8 -m pip install pip==${PIP_VERSION} \
  && pip3.8 install  --no-cache  -r requirements-base.txt \
  && scl enable devtoolset-9 bash \
  # required for detectron2 install on Mac M1
  && pip3.8 install --no-cache tensorboard>=2.12.2 \
  && pip3.8 install --no-cache "detectron2@git+https://github.com/facebookresearch/detectron2.git@e2ce8dc#egg=detectron2"

# fix openssl issue
RUN pip3.8 uninstall --yes urllib3 && \
  pip3.8 install urllib3==1.25.11

RUN python3.8 -c "import nltk; nltk.download('punkt')" && \
  python3.8 -c "import nltk; nltk.download('averaged_perceptron_tagger')" && \
  python3.8 -c "from unstructured.ingest.doc_processor.generalized import initialize; initialize()"

# NOTE(Crag): work around annoying complaint that sometimes occurs about /usr/local/bin/pip not existing
USER root
RUN ln -s /home/notebook-user/.local/bin/pip /usr/local/bin/pip
USER ${NB_USER}

COPY --chown=${NB_USER}:${NB_USER} CHANGELOG.md CHANGELOG.md
COPY --chown=${NB_USER}:${NB_USER} logger_config.yaml logger_config.yaml
COPY --chown=${NB_USER}:${NB_USER} prepline_${PIPELINE_PACKAGE}/ prepline_${PIPELINE_PACKAGE}/
COPY --chown=${NB_USER}:${NB_USER} exploration-notebooks exploration-notebooks
COPY --chown=${NB_USER}:${NB_USER} pipeline-notebooks pipeline-notebooks

ENTRYPOINT ["uvicorn", "prepline_general.api.app:app", \
  "--log-config", "logger_config.yaml", \
  "--host", "0.0.0.0"]
