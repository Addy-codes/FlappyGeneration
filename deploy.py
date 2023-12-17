import requests
import zipfile
import os
import time

# OAuth2 token and site ID
ACCESS_TOKEN = 'nfp_hdM39BoYGcbd74sMXeE5ZY7bDmCUD57K5a42'
SITE_ID = None  # Leave as None if creating a new site

# API Endpoints
DEPLOY_URL = f'https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys' if SITE_ID else 'https://api.netlify.com/api/v1/sites'

# Create a ZIP file of the website folder
def zip_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(folder_path, '..')))

# Deploy the site using the ZIP file
def deploy_site(zip_path):
    headers = {
        'Content-Type': 'application/zip',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }
    with open(zip_path, 'rb') as zipf:
        response = requests.post(DEPLOY_URL, headers=headers, data=zipf)
    return response.json()

def main():
    folder_path = './CustomFlappy'
    zip_path = 'website.zip'

    # Zip the website folder
    zip_folder(folder_path, zip_path)

    # Deploy the site
    deploy_response = deploy_site(zip_path)
    if 'id' in deploy_response:
        deploy_id = deploy_response['id']
        url = deploy_response['url']
        print(url)
        print(f"Deploy initiated. Deploy ID: {deploy_id}")

    else:
        print("Error in deployment:", deploy_response)

if __name__ == "__main__":
    main()
