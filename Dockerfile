FROM python:3.6-alpine

RUN apk add --no-cache git g++ make libstdc++ gnupg musl-dev && \
    mkdir /kapitan

WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY requirements.txt ./

# TODO: Remove '--prefix=/usr/local' once https://github.com/salt-formulas/reclass/pull/28 is merged
RUN pip install --upgrade --no-cache-dir pip && \
    pip install --prefix=/usr/local --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
