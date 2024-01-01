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

# Initialize the Gradio client
client = gradio_client.Client("https://eccv2022-dis-background-removal.hf.space/--replicas/l8swv/")

# AWS SES configuration
AWS_REGION = "eu-north-1"  # e.g., 'us-west-2'
SENDER_EMAIL = "ankurg@gmail.com"  # This should be a verified email in AWS SES

SITE_ID = None  # Leave as None if creating a new site
# API Endpoints
DEPLOY_URL = f'https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys' if SITE_ID else 'https://api.netlify.com/api/v1/sites'

def createGame(theme):
    print("Finding choice")
    game_choice = choice(theme)
    print(game_choice)

    if game_choice == 'flappy':
        # Flappy Bird specific processing
        prompt = f"""
            Given the theme '{theme}' for a Flappy Bird game, please provide ideas for the following elements, keep it short:
            1. Obstacle 1: This should represent something or someone the main character needs to avoid in the game environment, this obstacle is something that is preferably in the sky and would replace the top pipe.
            2. Obstacle 2: Another element in the game that poses a challenge to the main character that is preferably on the ground.
            3. Main Character: A representation of the main theme in a creative and thematic way.
            4. Background Image: A scene that sets the environment where the action takes place.
            """
        processed_theme = process_theme(prompt)
        parsed_theme = parse_processed_theme_flappy(processed_theme)
        print(parsed_theme)
        generate_flappyassets(parsed_theme['main_character'], parsed_theme['game_background'], parsed_theme['top_obstacle'], parsed_theme['bottom_obstacle'])
        folder_path = './CustomFlappy'
        zip_path = 'website.zip'
        url = deploy(folder_path, zip_path)
        return url
    elif game_choice == 'wackamole':
        # Whack-a-Mole specific processing
        prompt = f"""
        Given the theme '{theme}' for a Whack-a-Mole game, please provide creative ideas for the following elements, make sure the elements follow the theme, keep the description short and precise:
        1. Mole: A character or element that players will try to catch, find, or 'whack'.
        2. Hole: A representation of where this character or element can hide.
        3. Background Image: A visually rich scene that encapsulates the essence of '{theme}', providing an immersive backdrop for the game.
        """
        processed_theme = process_theme(prompt)
        parsed_theme = parse_processed_theme_wackamole(processed_theme)
        print(parsed_theme)
        generate_wackamoleassets(parsed_theme.mole, parsed_theme.hole, parsed_theme.game_background)
        folder_path = './CustomWackAMole'
        zip_path = 'WackAMole_website.zip'
        url = deploy(folder_path, zip_path)
        return url

def deploy(folder_path, zip_path):
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
        print(f"Deploy initiated. Deploy ID: {deploy_id}")

    else:
        print("Error in deployment:", deploy_response)
        return "Error in deployment"
    return url

def choice(theme):
    openai.api_key = OPENAI_API_KEY
    # Elaborate the prompt
    prompt = (
        f"I am planning a game based on the theme '{theme}'. I need to decide whether to create a game similar to Flappy Bird, "
        f"where the player controls a bird navigating through gaps between vertical obstacles, or a game similar to Whack-a-Mole, "
        f"where the player hits objects popping out from holes. Based on the theme '{theme}', which game would be more appropriate: Flappy Bird or Whack-a-Mole?"
    )

    try:
        # Send the prompt to OpenAI's GPT-4 model
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=50  # Adjust max_tokens based on expected response length
        )

        # Parse the response
        decision = response.choices[0].text.strip()
        print(decision)
        if "Flappy Bird" in decision:
            return "flappy"
        elif "Whack-a-Mole" in decision:
            return "wackamole"
        else:
            # In case the response is ambiguous or does not clearly mention either game
            return "undecided"

    except Exception as e:
        # Handle exceptions
        print(f"Error in connecting to OpenAI API: {e}")
        return None

def choice_pipeline(theme):
    openai.api_key = OPENAI_API_KEY
    # Elaborate the prompt
    prompt = (
        f"I am planning a game based on the theme '{theme}'. I need to decide whether to create a game similar to Flappy Bird, "
        f"where the player controls a bird navigating through gaps between vertical obstacles, or a game similar to Whack-a-Mole, "
        f"where the player hits objects popping out from holes. Based on the theme '{theme}', which game would be more appropriate: Flappy Bird or Whack-a-Mole?"
    )

    try:
        # Send the prompt to OpenAI's GPT-4 model
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=50  # Adjust max_tokens based on expected response length
        )

        # Parse the response
        decision = response.choices[0].text.strip()
        print(decision)
        if "Flappy Bird" in decision:
            return "flappy"
        elif "Whack-a-Mole" in decision:
            return "wackamole"
        else:
            # In case the response is ambiguous or does not clearly mention either game
            return "undecided"

    except Exception as e:
        # Handle exceptions
        print(f"Error in connecting to OpenAI API: {e}")
        return None

def process_theme(prompt):
    openai.api_key = OPENAI_API_KEY

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    processed_response = response.choices[0].text.strip()

    return processed_response

def parse_processed_theme_flappy(processed_theme_str):
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

def parse_processed_theme_wackamole(processed_theme_str):
    theme_dict = {}
    lines = processed_theme_str.split('\n')

    for line in lines:
        if 'Mole:' in line:
            theme_dict['mole'] = line.split(': ')[1]
        elif 'Hole:' in line:
            theme_dict['hole'] = line.split(': ')[1]
        elif 'Background Image:' in line:
            theme_dict['game_background'] = line.split(': ')[1]

    return theme_dict

def generate_flappyassets(main_character, background_image, obstacle1, obstacle2):
    out_dir = "./CustomFlappy/img"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    print("Generating Obs 1")
    generate_bot_pipe(obstacle1, out_dir)
    print("Generating Obs 2")
    generate_top_pipe(obstacle2, out_dir)
    print("Generating main character")
    generate_bird(main_character, f'{out_dir}/bird/v2.png', 'static/v2.png', (40, 62))
    remove_background(f"{out_dir}/bird/v2.png")
    print("Generating BG")
    generate_background(background_image, out_dir)

def generate_wackamoleassets(mole, hole, background_image):
    out_dir = "./CustomWackAMole/css"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    print(f"Generating {mole}")
    generate_bird(f"Face of {mole}", f"{out_dir}/mole.png", 'static/mole.png', (346, 413))
    remove_background(f"{out_dir}/mole.png")
    print(f"Generating {hole}")
    generate_bird(f"{hole}", f"{out_dir}/hole.png", 'static/hole.png', (210, 76))
    remove_background(f"{out_dir}/hole.png")
    print(f"Generating {background_image}")
    generate_bird(background_image, f"{out_dir}/background.png", 'static/background.png', (1920, 1080))

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

def remove_background(file_path):
    # Get the public URL of the image
    image_url = get_public_url(file_path)
    
    # Call the API to remove the background
    result = client.predict(image_url, api_name="/predict")
    processed_image_path = result[0]

    # Replace the original file with the new file
    shutil.move(processed_image_path, file_path)

    print(file_path)

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

def generate_bird(prompt, bird_path, static_bird_path, dimensions):
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
            "text": f"{prompt}, white clean background",
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

        # Decode the base64 image
        decoded_image = base64.b64decode(image["base64"])

        # Write to the original path
        with open(bird_path, "wb") as f:
            f.write(decoded_image)

        # Write to the static path
        with open(static_bird_path, "wb") as f:
            f.write(decoded_image)

    # remove_background(bird_path)
    resized_img = resize_image(bird_path, dimensions)
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