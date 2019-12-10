#!/bin/bash

ENV="prod"
DB_INSTANCE_ID="thesezvous-postgresql-prod3"

DATE=$(date +"%Y-%m-%dT%H-%M")

SNAPCHOT_NAME="$ENV"-"$DATE"

echo -e "\e[32m\e[1mActivate virtualenv\e[0m"
. /root/ve/bin/activate

echo -e "\e[32m\e[1mStop lambda $ENV\e[0m"
aws lambda put-function-concurrency --function-name task-"$ENV" --reserved-concurrent-executions 0

aws rds create-db-snapshot \
    --db-instance-identifier "$DB_INSTANCE_ID" \
    --db-snapshot-identifier "$SNAPCHOT_NAME"

aws rds wait db-snapshot-completed --db-snapshot-identifier "$SNAPCHOT_NAME"

echo -e "\e[32m\e[1mActivate lambda $ENV management\e[0m"
aws lambda delete-function-concurrency --function-name task-"$ENV"manage

echo -e "\e[32m\e[1mUpdate lambda $ENV\e[0m"
zappa update "$ENV"
echo -e "\e[32m\e[1mUpdate lambda $ENV management\e[0m"
zappa update "$ENV"manage
echo -e "\e[32m\e[1mMigrate via $ENV management\e[0m"
zappa manage "$ENV"manage migrate
echo -e "\e[32m\e[1mCollect static via $ENV management\e[0m"
zappa manage "$ENV"manage "collectstatic --noinput"

echo -e "\e[32m\e[1mStop lambda $ENV management\e[0m"
aws lambda put-function-concurrency --function-name task-"$ENV"manage --reserved-concurrent-executions 0
echo -e "\e[32m\e[1mActivate lambda $ENV\e[0m"
aws lambda delete-function-concurrency --function-name task-"$ENV"

echo -e "\e[32m\e[1mCheck status lambda $ENV\e[0m"
STATUS=$(curl -s -o /dev/null -w '%{http_code}' https://api.thesez-vous.org/admin/login/)
if [ "$STATUS" -eq 200 ]; then
    echo -e "Your updated Zappa deployment is \e[32m\e[1mlive\e[0m!: https://qfyxe6xy7d.execute-api.ca-central-1.amazonaws.com/devmanage"
else
    echo -e "Warning! Status check on the deployed lambda failed. A GET request to '/' yielded a \e[31m\e[1m$STATUS\e[0m response code."
fi