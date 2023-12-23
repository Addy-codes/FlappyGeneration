import os
import json
import boto3

BASE_PATH = os.getcwd()

# Loading the config.json file
config_path = os.path.join(BASE_PATH, 'keys', 'config.json')
with open(config_path) as f:
    config = json.load(f)

SECRET_KEY = "Addy-Codes"

# Assigning the keys to variables
STABILITY_API_KEY = config.get('stability_api_key')
CLIPDROP_API_KEY = config.get('clipdrop_api_key')
OPENAI_API_KEY = config.get('openai_api_key')
NETLIFY_ACCESS_TOKEN = config.get('netlify_access_token')
DB_BASE_URL='https://chao-game-backend.onrender.com/api/v1' 
client = boto3.client(
        'ses',
        region_name="eu-north-1",
        aws_access_key_id=config.get('aws_access_key_id'),
        aws_secret_access_key=config.get('aws_secret_access_key')
    )