# Build the virtualenv for Kapitan
FROM python:3.7-slim-stretch AS python-builder

RUN mkdir /kapitan
WORKDIR /kapitan

COPY ./kapitan ./kapitan
COPY ./MANIFEST.in ./MANIFEST.in
COPY ./requirements.txt ./requirements.txt
COPY ./setup.py ./setup.py

ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
    && python -m venv /opt/venv \
    && pip install --upgrade pip yq wheel \
    && pip install -r requirements.txt \
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
