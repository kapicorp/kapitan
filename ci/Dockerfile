FROM google/cloud-sdk:alpine

RUN apk add --no-cache python3-dev git g++ make libstdc++ gnupg musl-dev util-linux openssl coreutils && \
    python3 -m ensurepip && \
    rm -rf /usr/lib/python*/ensurepip && \
    pip3 install --upgrade --no-cache-dir pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    rm -rf /root/.cache

# TODO: Remove '--prefix=/usr/local' once https://github.com/salt-formulas/reclass/pull/28 is merged
RUN pip3 install --upgrade --prefix=/usr/local --no-cache-dir git+https://github.com/deepmind/kapitan.git --process-dependency-links

RUN gcloud components install kubectl
