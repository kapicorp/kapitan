# Build the virtualenv for Kapitan
FROM python:3.11-slim AS python-builder
ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH:-amd64}

RUN mkdir /kapitan
WORKDIR /kapitan

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential \
        git \
        default-jre

ENV POETRY_VERSION=1.8.3
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/go/bin:${PATH}"
RUN python -m venv $VIRTUAL_ENV \
    && pip install --upgrade pip yq wheel poetry==$POETRY_VERSION

# Install Go (for go-jsonnet)
RUN curl -fsSL -o go.tar.gz https://go.dev/dl/go1.24.2.linux-${TARGETARCH}.tar.gz \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz


COPY ./MANIFEST.in ./MANIFEST.in
COPY ./pyproject.toml ./pyproject.toml
COPY ./poetry.lock ./poetry.lock
COPY ./README.md ./README.md

# Installs and caches dependencies
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install --no-root --extras=gojsonnet --extras=reclass-rs --extras=omegaconf

COPY ./kapitan ./kapitan

RUN pip install .[gojsonnet,omegaconf,reclass-rs]

FROM golang:1 AS go-builder
RUN GOBIN=$(pwd)/ go install cuelang.org/go/cmd/cue@latest

# Final image with virtualenv built in previous step
FROM python:3.11-slim

ENV PATH="/opt/venv/bin:${PATH}"
ENV HELM_CACHE_HOME=".cache/helm"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

# Install runtime dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        ssh-client \
        gnupg \
        ca-certificates \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Helm repository

RUN curl -fsSL https://packages.buildkite.com/helm-linux/helm-debian/gpgkey | gpg --dearmor | tee /usr/share/keyrings/helm.gpg > /dev/null && \
	echo "deb [signed-by=/usr/share/keyrings/helm.gpg] https://packages.buildkite.com/helm-linux/helm-debian/any/ any main" | tee /etc/apt/sources.list.d/helm-stable-debian.list

# Install Helm
RUN apt-get update \
    && apt-get install --no-install-recommends -y helm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --no-log-init --user-group kapitan

COPY --from=go-builder /go/cue /usr/bin/cue
COPY --from=python-builder /opt/venv /opt/venv

USER kapitan

ENTRYPOINT ["kapitan"]
