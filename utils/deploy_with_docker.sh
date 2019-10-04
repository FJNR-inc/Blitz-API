#!/bin/bash

docker-compose run --rm \
api \
bash -c "bash ./utils/deploy_prod.sh"
