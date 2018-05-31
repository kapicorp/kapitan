FROM sparkprime/jsonnet AS jsonnet

FROM google/cloud-sdk:alpine

RUN apk add --no-cache python3-dev git g++ make libstdc++ gnupg musl-dev util-linux openssl openssl-dev libffi-dev coreutils yaml-dev jq ncurses terraform && \
    python3 -m ensurepip && \
    rm -rf /usr/lib/python*/ensurepip && \
    pip3 install --upgrade --no-cache-dir pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    rm -rf /root/.cache

RUN pip3 install --upgrade --no-cache-dir git+https://github.com/deepmind/kapitan.git

RUN gcloud components install kubectl

COPY --from=jsonnet /usr/local/bin/jsonnet /usr/local/bin/
