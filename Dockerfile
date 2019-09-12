FROM python:3.7-slim-stretch

RUN mkdir /kapitan
WORKDIR /kapitan
COPY kapitan/ kapitan/
COPY requirements.txt ./

RUN apt-get update && apt-get install -y \
    build-essential git wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# build go from source
RUN wget https://dl.google.com/go/go1.12.7.linux-amd64.tar.gz -q && \
    tar -C /usr/local -xvf go1.12.7.linux-amd64.tar.gz && \
    rm go1.12.7.linux-amd64.tar.gz

# build helm binding
RUN export PATH=$PATH:/usr/local/go/bin && \
    chmod +x kapitan/inputs/helm/build.sh && \
    ./kapitan/inputs/helm/build.sh && \
    rm /usr/local/go -rf

ENV PYTHONPATH="/kapitan/"
ENV SEARCHPATH="/src"
VOLUME ${SEARCHPATH}
WORKDIR ${SEARCHPATH}

ENTRYPOINT ["python", "-m", "kapitan"]
