#!/bin/bash

echo -e "\e[32m\e[1mActivate virtualenv\e[0m"
. /root/ve/bin/activate

echo -e "\e[32m\e[1mStop lambda prod\e[0m"
aws lambda put-function-concurrency --function-name task-prod --reserved-concurrent-executions 0
echo -e "\e[32m\e[1mActivate lambda prod management\e[0m"
aws lambda delete-function-concurrency --function-name task-prodmanage

echo -e "\e[32m\e[1mUpdate lambda prod\e[0m"
zappa update prod
echo -e "\e[32m\e[1mUpdate lambda prod management\e[0m"
zappa update prodmanage
echo -e "\e[32m\e[1mMigrate via prod management\e[0m"
zappa manage prodmanage migrate
echo -e "\e[32m\e[1mCollect static via prod management\e[0m"
zappa manage prodmanage "collectstatic --noinput"

echo -e "\e[32m\e[1mStop lambda prod management\e[0m"
aws lambda put-function-concurrency --function-name task-prodmanage --reserved-concurrent-executions 0
echo -e "\e[32m\e[1mActivate lambda prod\e[0m"
aws lambda delete-function-concurrency --function-name task-prod

echo -e "\e[32m\e[1mCheck status lambda prod\e[0m"
STATUS=$(curl -s -o /dev/null -w '%{http_code}' https://api.thesez-vous.org/admin/login/)
if [ $STATUS -eq 200 ]; then
    echo -e "Your updated Zappa deployment is \e[32m\e[1mlive\e[0m!: https://qfyxe6xy7d.execute-api.ca-central-1.amazonaws.com/devmanage"
else
    echo -e "Warning! Status check on the deployed lambda failed. A GET request to '/' yielded a \e[31m\e[1m$STATUS\e[0m response code."
fi