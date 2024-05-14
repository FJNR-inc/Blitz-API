FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential \
  # psycopg dependencies
  && apt-get install -y libpq-dev \
  # Translations dependencies
  && apt-get install -y gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/* \

WORKDIR /app

# Adds our application code to the image
COPY . .

RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt


COPY ./docker/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./docker/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

WORKDIR /opt/project

ENTRYPOINT ["/entrypoint"]