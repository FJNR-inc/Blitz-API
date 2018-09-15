import os
import json
from pathlib import Path

PARENT_FOLDER_PATH = Path(__file__).resolve().parents[1]
ZAPPA_SETTINGS_PATH = PARENT_FOLDER_PATH.joinpath('zappa_settings.json')

with open(str(ZAPPA_SETTINGS_PATH), 'r') as zappa_settings:
    data = json.load(zappa_settings)

for key, val in data['dev']['aws_environment_variables'].items():
    if val == "":
        data['dev']['aws_environment_variables'][key] = os.environ[key]

with open(str(ZAPPA_SETTINGS_PATH), 'w') as zappa_settings:
    json.dump(data, zappa_settings, indent=4)
