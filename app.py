from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import openai
from PIL import Image
import base64
import zipfile
import os
import requests
import gradio_client
import shutil
import threading
import boto3
from botocore.exceptions import ClientError
from config import(
    STABILITY_API_KEY,
    CLIPDROP_API_KEY,
    OPENAI_API_KEY,
    NETLIFY_ACCESS_TOKEN,
    SECRET_KEY,
    DB_BASE_URL
)

app = Flask(__name__)

app.secret_key = SECRET_KEY

# Initialize the Gradio client
client = gradio_client.Client("https://eccv2022-dis-background-removal.hf.space/--replicas/l8swv/")

SITE_ID = None  # Leave as None if creating a new site
# API Endpoints
DEPLOY_URL = f'https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys' if SITE_ID else 'https://api.netlify.com/api/v1/sites'

# AWS SES configuration
AWS_REGION = "eu-north-1"  # e.g., 'us-west-2'
SENDER_EMAIL = "ankurg@gmail.com"  # This should be a verified email in AWS SES



@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        # Save to MongoDB
        microservice_url = f"{DB_BASE_URL}/adduser"
        data = {'name': name, 'email': email, 'phone': phone}
        headers= {'Content-Type': 'application/json'}
        userId=None
        try:
            response = requests.post(microservice_url, json=data , headers = headers)
            if response.status_code == 200:
                print('Successfully Added In Db')
                userId = response.json().get('userId')
            else:
                print('Error While Adding In Db')
        except Exception as e:
            # Handle exceptions such as network errors
            print(f"Error: {e}")
        

        print(userId)

        # Save user info in session
        session['user_info'] = {'name': name, 'email': email, 'phone': phone ,'userId': userId}
        
        return redirect(url_for('theme'))

    return render_template('login.html')

@app.route('/theme', methods=['GET', 'POST'])       #hittt
def theme():
    if request.method == 'POST':
        if 'generate' in request.form:
            theme = request.form.get('theme')
            
            # Save to MongoDB
            microservice_url = f"{DB_BASE_URL}/addtheme"
            user=session.get('user_info')
            print(user['userId'])
            data = {'theme': theme, 'user': user['userId']}
            headers= {'Content-Type': 'application/json'}
            outputId=None
            try:
                response = requests.post(microservice_url, json=data , headers=headers)
                if response.status_code == 200:
                    print('Successfully Added In Db')
                    outputId=response.json().get('outputId')
                    print(outputId)
                else:
                    print('Error While Adding In Db')
                    print(response)
            except Exception as e:
                # Handle exceptions such as network errors
                print(f"Error: {e}")

            # Process the theme here
            processed_theme = process_theme(theme)  # Implement this function

            # Parse and save processed theme in session
            parsed_theme = parse_processed_theme(processed_theme)
            session['processed_theme'] = parsed_theme
            session['outputId']=outputId

            return render_template('modifytheme.html', processed_theme=parsed_theme)

    return render_template('theme.html')

@app.route('/modifytheme', methods=['GET', 'POST'])   
def modify_theme():
    if request.method == 'POST':
        main_character = request.form.get('main_character')
        game_background = request.form.get('game_background')
        top_obstacle = request.form.get('top_obstacle')
        bottom_obstacle = request.form.get('bottom_obstacle')



        # Store parameters in the session
        session['main_character'] = main_character
        session['game_background'] = game_background
        session['top_obstacle'] = top_obstacle
        session['bottom_obstacle'] = bottom_obstacle

        generate_assets(main_character, game_background, top_obstacle, bottom_obstacle)
        # For example, redirecting to another page with this data
        return redirect(url_for('assets'))  # Replace 'next_page' with your next page

    # Retrieve parsed processed theme from session
    processed_theme = session.get('processed_theme', {})
    return render_template('modifytheme.html', processed_theme=processed_theme)


@app.route('/assets', methods=['GET', 'POST'])
def assets():
    if request.method == 'POST':
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
            # Save to MongoDB
            microservice_url = f"{DB_BASE_URL}/addurl"
            outputId=session.get('outputId')
            data = {'url': url, 'output': outputId}
            headers= {'Content-Type': 'application/json'}
            try:
                response = requests.put(microservice_url, json=data , headers=headers)
                if response.status_code == 200:
                    print('Successfully Added In Db')
                else:
                    print('Error While Adding In Db')
            except Exception as e:
                # Handle exceptions such as network errors
                print(f"Error: {e}")
            session['url'] = url
            print(f"Deploy initiated. Deploy ID: {deploy_id}")

        else:
            print("Error in deployment:", deploy_response)
            return "Error in deployment"
        return redirect(url_for('final'))
    
    return render_template('assets.html')

@app.route('/final', methods=['GET', 'POST']) 
def final():
    url = session.get('url')
    # user_info = session.get('user_info')

    # if user_info and 'email' in user_info:
    #     send_email(user_info['email'], url)
    # else:
    #     print("Email was not found in the session")
    return render_template ("final.html", url = url)

@app.route('/regenerate/main_character', methods=['POST'])
def regenerate_main_character():
    # Regeneration logic for main character
    out_dir = "./CustomFlappy/img"
    main_character = session.get('main_character', '')
    generate_bird(main_character, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/top_obstacle', methods=['POST'])
def regenerate_top_obstacle():
    out_dir = "./CustomFlappy/img"
    top_obstacle = session.get('top_obstacle', '')
    generate_top_pipe(top_obstacle, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/bottom_obstacle', methods=['POST'])
def regenerate_bottom_obstacle():
    out_dir = "./CustomFlappy/img"
    bottom_obstacle = session.get('bottom_obstacle', '')
    generate_bot_pipe(bottom_obstacle, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/background', methods=['POST'])
def regenerate_background():
    out_dir = "./CustomFlappy/img"
    background_image = session.get('game_background', '')
    generate_background(background_image, out_dir)
    return redirect(url_for('assets'))


def process_theme(theme):
    openai.api_key = OPENAI_API_KEY

    prompt = f"""
    Breakdown the given theme: '{theme}' for a Flappy Bird game, into 4 items ie 2 Obstacles (something or someone the main character needs to avoid in the game environment), 1 Main Character and 1 Background. Compare the two obstacles and the one that's more likely to be on the ground should be Obstacle 1. give the output as follows:
    1. Obstacle 1: Replaces the bottom pipe from the original flappy bird game.
    2. Obstacle 2: Replaces the top pipe by being flipped upside down from the original flappy bird game.
    3. Main Character: Replaces the bird from the original flappy bird game.
    4. Background Image: A scene that sets the environment where the action takes place.
    """

    max_attempts = 3
    attempt_count = 0
    last_response = ""

    while attempt_count < max_attempts:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        processed_response = response.choices[0].text.strip()
        last_response = processed_response

        # Check if the response contains all four required items
        if ("Obstacle 1:" in processed_response and
            "Obstacle 2:" in processed_response and
            "Main Character:" in processed_response and
            "Background Image:" in processed_response):
            return processed_response

        attempt_count += 1

    # If no satisfactory response after max_attempts, return the last response
    return last_response

def parse_processed_theme(processed_theme_str):
    theme_dict = {}
    lines = processed_theme_str.split('\n')
    for line in lines:
        if 'Obstacle 1:' in line:
            theme_dict['top_obstacle'] = line.split(': ')[1]
        elif 'Obstacle 2:' in line:
            theme_dict['bottom_obstacle'] = line.split(': ')[1]
        elif 'Main Character:' in line:
            theme_dict['main_character'] = line.split(': ')[1]
        elif 'Background Image:' in line:
            theme_dict['game_background'] = line.split(': ')[1]

    return theme_dict

def generate_assets(main_character, background_image, obstacle1, obstacle2):
    out_dir = "./CustomFlappy/img"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    print("Generating Obs 1")
    generate_bot_pipe(obstacle1, out_dir)
    print("Generating Obs 2")
    generate_top_pipe(obstacle2, out_dir)
    print("Generating main character")
    generate_bird(main_character, out_dir)
    print("Generating BG")
    generate_background(background_image, out_dir)

def ttmgenerate_image(body, url="https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}",
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))
    return response.json()

def show_image(file_path):
    with Image.open(file_path) as img:
        img.show()

def resize_image(file_path, new_size):
    with Image.open(file_path) as img:
        resized_image = img.resize(new_size)
        return resized_image

def save_image(image, file_path):
    image.save(file_path)

def crop_transparency(image_path):
    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        pixels = img.load()

        width, height = img.size
        top, left, right = height, width, 0

        for y in range(height):
            for x in range(width):
                if pixels[x, y][3] != 0:
                    top = min(top, y)
                    left = min(left, x)
                    right = max(right, x)

        bottom = height
        return img.crop((left, top, right, bottom))

# def remove_background(file_path, api_key):
#     url = 'https://clipdrop-api.co/remove-background/v1'
#     with open(file_path, 'rb') as image_file:
#         files = {'image_file': (file_path, image_file, 'image/jpeg')}
#         headers = {'x-api-key': api_key}

#         response = requests.post(url, files=files, headers=headers)
#         if response.ok:
#             with open(file_path, 'wb') as out_file:
#                 out_file.write(response.content)
#             print(f"Background removed and image saved back as '{file_path}'")
#         else:
#             print(f"Error: {response.json()['error']}")
def remove_background(file_path):
    # Get the public URL of the image
    image_url = get_public_url(file_path)
    
    # Call the API to remove the background
    result = client.predict(image_url, api_name="/predict")

    # Assuming the result contains the path to the processed image
    processed_image_path = result[0]

    # Replace the original file with the new file
    shutil.move(processed_image_path, file_path)

    print(file_path)

    # Optional: Clean up any temporary directories created by Gradio
    temp_dir = os.path.dirname(processed_image_path)
    if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)

def get_public_url(file_path):
    """
    Uploads a file to 0x0.st and returns the URL.

    :param file_path: Path to the file to upload
    :return: URL of the uploaded file
    """
    with open(file_path, 'rb') as f:
        response = requests.post('https://0x0.st', files={'file': f})
    
    if response.status_code == 200:
        return response.text.strip()
    else:
        raise Exception(f"Error uploading file: {response.status_code}")


def generate_pipe_common(prompt, out_dir, position):
    image_generation_body = {
        "steps": 40,
        "width": 640,
        "height": 1536,
        "seed": 0,
        "cfg_scale": 10,
        "samples": 1,
        "style_preset": "pixel-art",
        "text_prompts": [
            {"text": f"A tall image of {prompt}, white clean background", "weight": 1},
            {"text": "blurry, bad", "weight": -1}
        ],
    }

    # Generate image
    generated_data = ttmgenerate_image(image_generation_body)
    image_path = f'{out_dir}/{position}pipe.png'
    static_image_path = f'./static/{position}pipe.png'
    for i, image in enumerate(generated_data["artifacts"]):
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))
        with open(static_image_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))

    return image_path

def crop_rotate_resize_save(image_path, position, out_dir):
    # Crop the image to remove transparent space
    cropped_img = crop_transparency(image_path)
    cropped_img.save(image_path)

    # Check position and rotate if needed
    if position == "top":
        with Image.open(image_path) as img:
            rotated_img = img.rotate(180)
            rotated_img.save(image_path)

    # Assuming remove_background and resize_image are defined elsewhere
    remove_background(image_path)
    resized_img = resize_image(image_path, (82, 450))
    save_image(resized_img, f'{out_dir}/{position}pipe.png')

def generate_top_pipe(prompt, out_dir):
    image_path = generate_pipe_common(prompt, out_dir, "top")
    crop_rotate_resize_save(image_path, "top", out_dir)

def generate_bot_pipe(prompt, out_dir):
    image_path = generate_pipe_common(prompt, out_dir, "bot")
    crop_rotate_resize_save(image_path, "bot", out_dir)
def generate_bird(prompt, out_dir):
    # Generate bird
    image_generation_body = {
        "steps": 40,
        "width": 1024,
        "height": 1024,
        "seed": 0,
        "cfg_scale": 10,
        "samples": 1,
        "style_preset": "pixel-art",
        "text_prompts": [
            {
            "text": f"A full image of {prompt}, white clean background",
            "weight": 1
            },
            {
            "text": "blurry, bad",
            "weight": -1
            }
        ],
    }
    # Generate image
    generated_data = ttmgenerate_image(image_generation_body)
    for i, image in enumerate(generated_data["artifacts"]):
        # Original path
        bird_path = f'{out_dir}/bird/v2.png'
        
        # Path in the static directory
        static_bird_path = 'static/v2.png'

        # Decode the base64 image
        decoded_image = base64.b64decode(image["base64"])

        # Write to the original path
        with open(bird_path, "wb") as f:
            f.write(decoded_image)

        # Write to the static path
        with open(static_bird_path, "wb") as f:
            f.write(decoded_image)

    remove_background(bird_path)
    resized_img = resize_image(bird_path, (40, 62))
    save_image(resized_img, bird_path)
    # save_image(resized_img,"./static/v2.png")

def generate_background(prompt, out_dir):
    # Generate Background
    image_generation_body = {
        "steps": 40,
        "width": 1024,
        "height": 1024,
        "seed": 0,
        "cfg_scale": 10,
        "samples": 1,
        "style_preset": "pixel-art",
        "text_prompts": [
            {
            "text": prompt,
            "weight": 1
            },
            {
            "text": "blurry, bad",
            "weight": -1
            }
        ],
    }

    # Generate image
    generated_data = ttmgenerate_image(image_generation_body)
    for i, image in enumerate(generated_data["artifacts"]):
        bg_path = f'{out_dir}/BG.png'
        with open(bg_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))

    resized_img = resize_image(bg_path, (1000,1000))
    save_image(resized_img, bg_path)
    save_image(resized_img,"./static/BG.png")
    width, height = resized_img.size
    crop_area = (0, height - 112, 700, height)  # left, upper, right, lower
    cropped_img = resized_img.crop(crop_area)
    ground_image_path = f'{out_dir}/ground.png'
    cropped_img.save(ground_image_path)
    cropped_img.save("./static/ground.png")

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
        'Authorization': f'Bearer {NETLIFY_ACCESS_TOKEN}'
    }
    with open(zip_path, 'rb') as zipf:
        response = requests.post(DEPLOY_URL, headers=headers, data=zipf)
    return response.json()

def send_email(recipient, game_url):
    # The subject line for the email.
    subject = "Game URL"

    # The email body for recipients with non-HTML email clients.
    body_text = f"Here is your game URL: {game_url}"

    # The HTML body of the email.
    body_html = f"""<html>
    <head></head>
    <body>
      <h1>Game URL</h1>
      <p>Here is your game URL: <a href="{game_url}">{game_url}</a></p>
    </body>
    </html>"""

    # The character encoding for the email.
    charset = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses', region_name=AWS_REGION)

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html,
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject,
                },
            },
            Source=SENDER_EMAIL,
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

if __name__ == '__main__':
    app.run(debug=True)
