#!/bin/bash

echo -e "\e[7m Starting Docker container... \e[27m"
docker-compose run --rm \
-e AWS_ACCESS_KEY_ID=$1 \
-e AWS_SECRET_ACCESS_KEY=$2 \
api \
bash -c "\
. ~/ve/bin/activate && \
zappa update prod && \
zappa manage prod migrate && \
zappa manage prod \"collectstatic --noinput\""
