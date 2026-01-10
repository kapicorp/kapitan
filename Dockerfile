# Build the virtualenv for Kapitan
ARG VIRTUAL_ENV_PATH=/opt/venv
ARG PYTHON_VERSION=3.11
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie-slim AS python-builder
ARG VIRTUAL_ENV_PATH
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

ENV VIRTUAL_ENV=${VIRTUAL_ENV_PATH}
ENV PATH="${VIRTUAL_ENV}/bin:/usr/local/go/bin:${PATH}"
RUN uv venv ${VIRTUAL_ENV} && \
    uv pip install yq wheel

# Install Go (for go-jsonnet)
RUN curl -fsSL -o go.tar.gz https://go.dev/dl/go1.24.2.linux-${TARGETARCH}.tar.gz \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz


COPY ./MANIFEST.in ./MANIFEST.in
COPY ./pyproject.toml ./pyproject.toml
COPY ./uv.lock ./uv.lock
COPY ./README.md ./README.md
COPY ./kapitan/version.py ./kapitan/version.py

RUN uv sync --locked --all-extras

COPY ./kapitan ./kapitan

RUN uv pip install .[gojsonnet,omegaconf,reclass-rs]


ARG PYTHON_VERSION=3.11
FROM golang:1 AS go-builder
RUN GOBIN=$(pwd)/ go install cuelang.org/go/cmd/cue@latest

# Final image with virtualenv built in previous step
ARG PYTHON_VERSION=3.11
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie-slim
ARG VIRTUAL_ENV_PATH=/opt/venv

ENV VIRTUAL_ENV=${VIRTUAL_ENV_PATH}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
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
COPY --from=python-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

USER kapitan

ENTRYPOINT ["kapitan"]
