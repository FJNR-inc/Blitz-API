#!/bin/bash

docker-compose run --rm \
-e AWS_ACCESS_KEY_ID=$1 \
-e AWS_SECRET_ACCESS_KEY=$2 \
api \
bash -c "bash ./utils/deploy_prod.sh"
