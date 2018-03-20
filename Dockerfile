FROM python:3.6-alpine

RUN apk --update add git g++ make libstdc++ gnupg musl-dev \
    && rm -rf /var/cache/apk/* \
    && mkdir /kapitan

WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY requirements.txt ./

RUN pip install --upgrade --no-cache-dir pip \
    && pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
