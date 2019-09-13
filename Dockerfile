# First build the Helm binding
FROM golang:1.12.9-stretch AS go-builder

RUN mkdir /kapitan
WORKDIR /kapitan
COPY . .

RUN ./kapitan/inputs/helm/build.sh

# Build the virtualenv for Kapitan
FROM python:3.7-slim-stretch AS python-builder

COPY --from=go-builder /kapitan /kapitan
WORKDIR /kapitan

ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        gcc \
    && python -m venv /opt/venv \
    && pip install --upgrade \
        pip \
        setuptools \
        wheel \
    && pip install -r requirements.txt \
    && ./kapitan/inputs/helm/build.sh \
    && pip install .

# Final image with virtualenv built in previous step
FROM python:3.7-slim-stretch

COPY --from=python-builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

# Install runtime dependencies and run as a non-root user for good measure
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        git \
        gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --no-log-init --user-group kapitan

USER 1000

ENTRYPOINT ["kapitan"]
