#!/bin/bash

if [ "$TRAVIS_BRANCH" == "develop" ] && [ "$TRAVIS_REPO_SLUG" == "FJNR-inc/Blitz-API" ] && [ "${TRAVIS_PULL_REQUEST}" = "false" ]; then
    CURRENT_DIR=$(readlink -f $0)
    PARENT_DIR="${CURRENT_DIR%/*/*}"
    echo -e "\e[7m Starting Docker container... \e[27m"
    docker run \
    -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY \
    -e DEBUG \
    -e ALLOWED_HOSTS \
    -e ORGANIZATION \
    -e EMAIL_SERVICE \
    -e AUTO_ACTIVATE_USER \
    -e ACTIVATION_URL \
    -e FORGOT_PASSWORD_URL \
    -e AWS_S3_REGION_NAME \
    -e AWS_STORAGE_STATIC_BUCKET_NAME \
    -e AWS_STORAGE_MEDIA_BUCKET_NAME \
    -e AWS_S3_STATIC_CUSTOM_DOMAIN \
    -e AWS_S3_MEDIA_CUSTOM_DOMAIN \
    -e STATIC_URL \
    -e STATICFILES_STORAGE \
    -e MEDIA_URL \
    -e MEDIA_ROOT \
    -e DEFAULT_FILE_STORAGE \
    -e CONFIRM_SIGN_UP \
    -e FORGOT_PASSWORD \
    -e EMAIL_BACKEND \
    -e DEFAULT_FROM_EMAIL \
    -e PAYSAFE_BASE_URL \
    -e PAYSAFE_VAULT_URL \
    -e PAYSAFE_CARD_URL \
    -e EMAIL_HOST_USER \
    -e ADMINS \
    -e SENDINBLUE_API_KEY \
    -e SECRET_KEY \
    -e DATABASE_URL \
    -e PAYSAFE_ACCOUNT_NUMBER \
    -e PAYSAFE_USER \
    -e PAYSAFE_PASSWORD \
    -e EMAIL_HOST_PASSWORD \
    -e EXTERNAL_SCHEDULER_USER \
    -e EXTERNAL_SCHEDULER_PASSWORD \
    -ti -v $PARENT_DIR:/var/task lambci/lambda:build-python3.6 bash -c "\
    echo -e \"\e[7m Initializing virtualenv... \e[27m\" && \
    virtualenv env && \
    . env/bin/activate && \
    echo -e \"\e[7m Installing pip requirements... \e[27m\" && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt && \
    zappa update dev && \
    zappa manage dev migrate && \
    zappa manage dev \"collectstatic --noinput\""
else
    echo "skip deploy since we are not on fjnr-inc/develop branch"
fi