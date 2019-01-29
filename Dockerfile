FROM python:3.7-alpine

RUN mkdir /kapitan
WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY requirements.txt ./

RUN apk add --no-cache --virtual build-dependencies g++ make musl-dev && \
    apk add --no-cache libstdc++ gnupg yaml-dev libffi-dev openssl-dev && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apk del build-dependencies && \
    rm -r /root/.cache

ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
