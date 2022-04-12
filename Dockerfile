# Build the virtualenv for Kapitan
FROM python:3.7-slim AS python-builder

RUN mkdir /kapitan
WORKDIR /kapitan

COPY ./kapitan ./kapitan
COPY ./MANIFEST.in ./MANIFEST.in
COPY ./requirements.txt ./requirements.txt
COPY ./setup.py ./setup.py

ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential

# Install Go (for go-jsonnet)
RUN curl -fsSL -o go.tar.gz https://go.dev/dl/go1.17.3.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go.tar.gz \
    && rm go.tar.gz

RUN python -m venv /opt/venv \
    && pip install --upgrade pip yq wheel \
    && export PATH=$PATH:/usr/local/go/bin \
    && pip install -r requirements.txt \
    && pip install .[gojsonnet]

# Install Helm
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 \
    && chmod 700 get_helm.sh \
    && HELM_INSTALL_DIR=/opt/venv/bin ./get_helm.sh --no-sudo \
    && rm get_helm.sh

# Final image with virtualenv built in previous step
FROM python:3.7-slim

COPY --from=python-builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

# Install runtime dependencies and run as a non-root user for good measure
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        ssh-client \
        gnupg \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --no-log-init --user-group kapitan

USER kapitan

ENTRYPOINT ["kapitan"]
