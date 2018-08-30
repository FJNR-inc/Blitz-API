import os
import json

with open('zappa_settings.json', 'r') as zappa_settings:
    data = json.load(zappa_settings)

for key, val in data['dev']['aws_environment_variables'].items():
    if val == "":
        data['dev']['aws_environment_variables'][key] = os.environ[key]

with open('zappa_settings.json', 'w') as zappa_settings:
    json.dump(data, zappa_settings, indent=4)
