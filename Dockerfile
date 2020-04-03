# First build the Helm binding
FROM golang:1.12.9-stretch AS helm-builder

RUN mkdir /kapitan
WORKDIR /kapitan

COPY ./kapitan ./kapitan
COPY ./MANIFEST.in ./MANIFEST.in
COPY ./requirements.txt ./requirements.txt
COPY ./setup.py ./setup.py

RUN chmod +x ./kapitan/inputs/helm/build.sh \
    && ./kapitan/inputs/helm/build.sh

# Build the virtualenv for Kapitan
FROM python:3.7-slim-stretch AS python-builder

COPY --from=helm-builder /kapitan /kapitan
WORKDIR /kapitan

ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
    && python -m venv /opt/venv \
    && pip install --upgrade pip yq \
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
        ssh-client \
        gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --no-log-init --user-group kapitan

USER kapitan

ENTRYPOINT ["kapitan"]
