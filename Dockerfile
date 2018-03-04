FROM alpine

RUN apk --update add --virtual build-dependencies build-base python-dev py-pip && \ 
    apk --update add python libstdc++ gnupg && mkdir /kapitan
WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && apk del build-dependencies


ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
