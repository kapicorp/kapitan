FROM sparkprime/jsonnet AS jsonnet

FROM golang:1.12 AS promtool

RUN go get -u github.com/prometheus/prometheus/cmd/promtool

FROM google/cloud-sdk:alpine

RUN apk add --no-cache python3-dev git g++ make libstdc++ gnupg musl-dev util-linux openssl openssl-dev libffi-dev coreutils yaml-dev jq ncurses && \
    python3 -m ensurepip && \
    rm -rf /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools yq && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    rm -rf /root/.cache

COPY setup.py requirements.txt MANIFEST.in /kapitan/
COPY kapitan /kapitan/kapitan/
RUN pip3 install -e /kapitan

ENV TERRAFORM_VERSION=0.11.13
ENV TERRAFORM_URL=https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip
RUN curl -o /tmp/terraform_${TERRAFORM_VERSION}.zip ${TERRAFORM_URL} && \
        unzip -d /usr/local/bin /tmp/terraform_${TERRAFORM_VERSION}.zip && \
        rm /tmp/terraform_${TERRAFORM_VERSION}.zip

RUN gcloud components install kubectl

COPY --from=jsonnet /usr/local/bin/jsonnet /usr/local/bin/
COPY --from=promtool /go/bin/promtool /usr/local/bin/
