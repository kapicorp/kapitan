# Build the virtualenv for Kapitan
FROM python:3.8-slim AS python-builder
ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH:-amd64}

RUN mkdir /kapitan
WORKDIR /kapitan

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential

ENV POETRY_VERSION=1.4.0
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/go/bin:${PATH}"
RUN python -m venv $VIRTUAL_ENV \
    && pip install --upgrade pip yq wheel poetry==$POETRY_VERSION

# Install Go (for go-jsonnet)
RUN curl -fsSL -o go.tar.gz https://go.dev/dl/go1.20.8.linux-${TARGETARCH}.tar.gz \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz

# Install Helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 \
    && chmod 700 get_helm.sh \
    && HELM_INSTALL_DIR=/opt/venv/bin ./get_helm.sh --no-sudo \
    && rm get_helm.sh


COPY ./MANIFEST.in ./MANIFEST.in
COPY ./pyproject.toml ./pyproject.toml
COPY ./poetry.lock ./poetry.lock
COPY ./README.md ./README.md

RUN poetry install --no-root --with=gojsonnet

COPY ./kapitan ./kapitan
RUN pip install .

FROM python-builder AS python-tester

RUN poetry install --no-root --with=test

ENTRYPOINT [ "pytest", "tests" ]

# Final image with virtualenv built in previous step
FROM python:3.8-slim

ENV PATH="/opt/venv/bin:${PATH}"
ENV HELM_CACHE_HOME=".cache/helm"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

# Install runtime dependencies and run as a non-root user for good measure
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        ssh-client \
        libmagic1 \
        gnupg \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --no-log-init --user-group kapitan

COPY --from=python-builder /opt/venv /opt/venv

USER kapitan

ENTRYPOINT ["kapitan"]
