FROM deepmind/kapitan:latest

RUN apk add --update --no-cache rsync

COPY entrypoint.sh /kapitan

ENTRYPOINT ["/bin/sh", "/kapitan/entrypoint.sh"]
