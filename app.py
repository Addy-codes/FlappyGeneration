from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import openai
from PIL import Image
import base64
import os
import requests
import threading
from config import(
    STABILITY_API_KEY,
    CLIPDROP_API_KEY,
    OPENAI_API_KEY,
    NETLIFY_ACCESS_TOKEN,
    SECRET_KEY,
)

app = Flask(__name__)

app.secret_key = SECRET_KEY


# MongoDB connection
client = MongoClient("mongodb_uri")  # replace with your MongoDB URI
db = client.your_database_name  # replace with your database name
users_collection = db.users  # replace with your collection name

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
        # users_collection.insert_one({'name': name, 'email': email, 'phone': phone})

        # Save user info in session
        session['user_info'] = {'name': name, 'email': email, 'phone': phone}
        
        return redirect(url_for('theme'))

    return render_template('login.html')

@app.route('/theme', methods=['GET', 'POST'])
def theme():
    if request.method == 'POST':
        if 'generate' in request.form:
            theme = request.form.get('theme')
            # Process the theme here
            processed_theme = process_theme(theme)  # Implement this function

            # Parse and save processed theme in session
            parsed_theme = parse_processed_theme(processed_theme)
            session['processed_theme'] = parsed_theme

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
    # Your assets page logic
    return render_template('assets.html')

@app.route('/regenerate/main_character', methods=['POST'])
def regenerate_main_character():
    # Regeneration logic for main character
    out_dir = "./CustomFlappy/img"
    main_character = session.get('main_character', '')
    generate_pipe(main_character, out_dir, "bottom")
    return redirect(url_for('assets'))

@app.route('/regenerate/top_obstacle', methods=['POST'])
def regenerate_top_obstacle():
    out_dir = "./CustomFlappy/img"
    top_obstacle = session.get('top_obstacle', '')
    generate_pipe(top_obstacle, out_dir, "top")
    return redirect(url_for('assets'))

@app.route('/regenerate/bottom_obstacle', methods=['POST'])
def regenerate_bottom_obstacle():
    out_dir = "./CustomFlappy/img"
    bottom_obstacle = session.get('bottom_obstacle', '')
    generate_pipe(bottom_obstacle, out_dir, "bottom")
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

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )

    return response.choices[0].text.strip()

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
    generate_pipe(obstacle1, out_dir, "bottom")
    print("Generating Obs 2")
    generate_pipe(obstacle2, out_dir, "top")
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

def remove_background(file_path, api_key):
    url = 'https://clipdrop-api.co/remove-background/v1'
    with open(file_path, 'rb') as image_file:
        files = {'image_file': (file_path, image_file, 'image/jpeg')}
        headers = {'x-api-key': api_key}

        response = requests.post(url, files=files, headers=headers)
        if response.ok:
            with open(file_path, 'wb') as out_file:
                out_file.write(response.content)
            print(f"Background removed and image saved back as '{file_path}'")
        else:
            print(f"Error: {response.json()['error']}")


def generate_pipe(prompt, out_dir, position):
    image_generation_body = {
        "steps": 40,
        "width": 640,
        "height": 1536,
        "seed": 0,
        "cfg_scale": 10,
        "samples": 1,
        "style_preset": "pixel-art",
        "text_prompts": [
            {"text": f"{prompt}, white clean background", "weight": 1},
            {"text": "blurry, bad", "weight": -1}
        ],
    }

    # Generate image
    generated_data = ttmgenerate_image(image_generation_body)
    for i, image in enumerate(generated_data["artifacts"]):
        image_path = f'{out_dir}/toppipe.png'
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))
    
    # Crop the image to remove transparent space
    cropped_img = crop_transparency(image_path)
    cropped_img.save(image_path)

    # Check position and rotate if needed
    if position == "top":
        with Image.open(image_path) as img:
            rotated_img = img.rotate(180)
            rotated_img.save(image_path)

    # Assuming remove_background and resize_image are defined elsewhere
    remove_background(image_path, CLIPDROP_API_KEY)
    resized_img = resize_image(image_path, (82, 450))
    save_image(resized_img, image_path)

    if position == "top":
        remove_background(image_path, CLIPDROP_API_KEY)
        resized_img = resize_image(image_path, (82, 450))
        save_image(resized_img, f'{out_dir}/toppipe.png')
        save_image(resized_img, './static/toppipe.png')
    else:
        remove_background(image_path, CLIPDROP_API_KEY)
        resized_img = resize_image(image_path, (82, 450))
        save_image(resized_img, f'{out_dir}/botpipe.png')
        save_image(resized_img, './static/botpipe.png')

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
        bird_path = f'{out_dir}/bird/v2.png'
        with open(bird_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))

    remove_background(bird_path, CLIPDROP_API_KEY)
    resized_img = resize_image(bird_path, (40, 62))
    save_image(resized_img, bird_path)
    save_image(resized_img,"./static/v2.png")

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

if __name__ == '__main__':
    app.run(debug=True)
