# /bin/terraform
FROM hashicorp/terraform:0.12.12 AS terraform-binary

# /bin/jsonnet
FROM bitnami/jsonnet:0.14.0 as jsonnet-binary

# /bin/promtool
FROM quay.io/prometheus/prometheus:v2.12.0 AS prometheus-binary

# Build the Helm binding
FROM golang:1.12-stretch AS helm-builder

RUN mkdir /kapitan
WORKDIR /kapitan

COPY ./kapitan ./kapitan
COPY ./MANIFEST.in ./MANIFEST.in
COPY ./requirements.txt ./requirements.txt
COPY ./setup.py ./setup.py

RUN chmod +x ./kapitan/inputs/helm/build.sh \
    && ./kapitan/inputs/helm/build.sh

# Build final image
FROM python:3.7-buster

ARG CLOUD_SDK_VERSION=274.0.0

ENV CLOUD_SDK_VERSION=$CLOUD_SDK_VERSION
ENV KAPP_URL=https://github.com/k14s/kapp/releases/download/v0.14.0/kapp-linux-amd64
ENV KBLD_URL=https://github.com/k14s/kbld/releases/download/v0.11.0/kbld-linux-amd64
ENV PATH="/opt/venv/bin:${PATH}"

COPY --from=terraform-binary /bin/terraform /usr/bin/terraform
COPY --from=jsonnet-binary /opt/bitnami/jsonnet/bin/jsonnet /usr/bin/jsonnet
COPY --from=jsonnet-binary /opt/bitnami/jsonnet/bin/jsonnetfmt /usr/bin/jsonnetfmt
COPY --from=prometheus-binary /bin/promtool /usr/bin/promtool
COPY --from=helm-builder /kapitan /kapitan

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        apt-transport-https \
        bash \
        bsdmainutils \
        build-essential \
        curl \
        docker.io \
        git \
        gnupg \
        jq \
        lsb-release \
        wget \
        zip \
    && export CLOUD_SDK_REPO="cloud-sdk-$(lsb_release -c -s)" \
    && echo "deb https://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && apt-get update \
    && apt-get install -y \
        google-cloud-sdk=${CLOUD_SDK_VERSION}-0 \
        kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # If True, anonymous statistics on SDK usage will not be collected.
    && gcloud config set core/disable_usage_reporting true \
    # If True, Cloud SDK will not automatically check for updates.
    && gcloud config set component_manager/disable_update_check true \
    # Metrics namespace for server side analytics
    && gcloud config set metrics/environment github_docker_image \
    && python -m venv /opt/venv \
    && pip install --upgrade pip yq \
    && pip install -r ./kapitan/requirements.txt \
    && ./kapitan/kapitan/inputs/helm/build.sh \
    && pip install ./kapitan \
    && rm -rf ./kapitan \
    && curl -L -o /usr/local/bin/kapp ${KAPP_URL} \
    && chmod +x /usr/local/bin/kapp \
    && curl -L -o /usr/local/bin/kbld ${KBLD_URL} \
    && chmod +x /usr/local/bin/kbld \
    && gcloud --version \
    && kubectl version --client \
    && terraform --version

VOLUME ["/root/.config"]

CMD ["/bin/bash"]
