from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import openai
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

        generate_assets()
        # Process this data or store it as needed
        # For example, redirecting to another page with this data
        return redirect(url_for('assets'))  # Replace 'next_page' with your next page

    # Retrieve parsed processed theme from session
    processed_theme = session.get('processed_theme', {})
    return render_template('modifytheme.html', processed_theme=processed_theme)


@app.route('/assets')
def assets():
    # Your assets page logic
    return render_template('assets.html')

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

def generate_assets():
    pass


if __name__ == '__main__':
    app.run(debug=True)
