FROM python:3.6-alpine

RUN apk add --no-cache git g++ make libstdc++ gnupg musl-dev yaml-dev libffi-dev openssl-dev && \
    mkdir /kapitan

WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY reclass ./
COPY requirements.txt ./

RUN pip install --upgrade --no-cache-dir pip && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
