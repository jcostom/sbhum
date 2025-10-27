FROM python:3.14.0-slim-bookworm AS builder

ARG TZ=America/New_York

RUN apt update && DEBIAN_FRONTEND=noninteractive apt -yq install gcc make
RUN \
    pip install requests \
    && pip install python-kasa==0.6.2.1 \
    && pip install influxdb-client \
    && pip cache purge

FROM python:3.14.0-slim-bookworm

ARG TZ=America/New_York
ARG PYVER=3.14

COPY --from=builder /usr/local/lib/python$PYVER/site-packages/ /usr/local/lib/python$PYVER/site-packages/

RUN mkdir /app
COPY ./sbhum.py /app
RUN chmod 755 /app/sbhum.py

ENTRYPOINT [ "python3", "-u", "/app/sbhum.py" ]
