import os
import json

BASE_PATH = os.getcwd()

# Loading the config.json file
config_path = os.path.join(BASE_PATH, 'key', 'config.json')
with open(config_path) as f:
    config = json.load(f)

# Assigning the keys to variables
STABILITY_API_KEY = config.get('stability_api_key')
CLIPDROP_API_KEY = config.get('clipdrop_api_key')
OPENAI_API_KEY = config.get('openai_api_key')
NETLIFY_ACCESS_TOKEN = config.get('netlify_access_token')
