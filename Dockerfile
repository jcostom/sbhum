FROM python:slim

ENV TZ=America/New_York

RUN \
    pip install requests \
    && pip install python-kasa \
    && pip install influxdb-client \
    && pip cache purge

RUN mkdir /app
COPY ./sbhum.py /app
RUN chmod 755 /app/sbhum.py

ENTRYPOINT [ "python3", "-u", "/app/sbhum.py" ]