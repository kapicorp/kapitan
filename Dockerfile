FROM python:3.6-alpine

RUN apk add --update --no-cache git g++ make libstdc++ gnupg musl-dev && \
    mkdir /kapitan

WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY requirements.txt ./

RUN pip install --upgrade --no-cache-dir pip && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
