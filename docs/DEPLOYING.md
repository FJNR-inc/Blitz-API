# Deploying to the development server

The development branch already has continuous deployment enabled. Every time a new commit is pushed to
the `develop` branch of this project, unit tests are executed and the updated version is deployed is the tests are successful.
To mimick AWS Lambda's environment, we use a special Docker container (lambci/lambda:build-python3.6). That allows us to recreate the same environment
anywhere, be it on a development PC or Travis.

## .travis.yml

This file is pretty straightforward. It dictates Travis what to do.

It contains some sensitive information in the form of encrypted environment variables:

- SENDINBLUE_API_KEY
- SECRET_KEY
- DATABASE_URL
- PAYSAFE_ACCOUNT_NUMBER
- PAYSAFE_USER
- PAYSAFE_PASSWORD
- EMAIL_HOST_PASSWORD
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY

Those, along with the unencrypted  variables, are used by Travis during the unit tests and used
to set up Zappa settings before deployment.

**NOTE: If you inspect the settings.py file, you'll see that some settings are overwritten when in "test" mode.
For example, the database used in unit tests will always be a sqlite3 database, regardless of the DATABASE_URL
environment variable you set.**

## write_secure_env.py

That script is executed by Travis to fill the empty variables in `zappa_settings.json`.
Travis is the only one to be able to decrypt the variables mentionned above, thus explaining the need for this script.

## deploy.sh

This script automatize the environement creation and the deployment.

An initial deployment with zappa is done with `zappa deploy <stage>`, where stage can be any string. That part
is usually done by hand by a developer. It creates the necessary infrastructure on AWS.

For the continuous deployment, we simply update the already deployed application using:
`zappa update dev`: pack the local environment and send it the S3 bucket.
`zappa manage dev migrate`: applies migration on the deployed app (== ./manage.py migrate).

## zappa_settings.json

This is the core configuration for the deployment. Zappa is the tool used to simplify AWS infrastructure creation.

The `aws_environment_variables` holds the environment variables that will be passed to the AWS Lambda.
Since there are secure variables, we leave them empty and let Travis fill them up before deploying (write_secure_env.py).


# Deploying a production version

For a production version, the same steps are done manually.

As of now, the AWS infrastructure is created by hand. Refer to our infrastructure documentation for more informations.
