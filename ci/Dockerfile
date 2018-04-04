FROM google/cloud-sdk:alpine

RUN apk add --update --no-cache python3-dev git g++ make libstdc++ gnupg musl-dev util-linux && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade --no-cache-dir pip setuptools && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    rm -r /root/.cache

RUN pip3 install --no-cache-dir git+https://github.com/deepmind/kapitan.git --process-dependency-links

RUN gcloud components install kubectl
