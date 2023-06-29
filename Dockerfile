FROM lambci/lambda:build-python3.8

LABEL maintainer="support@fjnr.ca"

COPY requirements.txt /requirements.txt
COPY requirements-dev.txt /requirements-dev.txt

RUN pip --timeout=1000 --no-cache-dir install -r /requirements.txt
RUN pip --timeout=1000 --no-cache-dir install -r /requirements-dev.txt

RUN mkdir -p /opt/project

COPY ./docker/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./docker/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

WORKDIR /opt/project

ENTRYPOINT ["/entrypoint"]