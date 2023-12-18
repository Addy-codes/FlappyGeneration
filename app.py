from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import openai
from config import(
    STABILITY_API_KEY,
    CLIPDROP_API_KEY,
    OPENAI_API_KEY,
    NETLIFY_ACCESS_TOKEN,
)

app = Flask(__name__)

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
        users_collection.insert_one({'name': name, 'email': email, 'phone': phone})
        
        return redirect(url_for('theme'))

    return render_template('login.html')

@app.route('/theme', methods=['GET', 'POST'])
def theme():
    if request.method == 'POST':
        if 'generate' in request.form:
            theme = request.form.get('theme')
            # Process the theme here
            processed_theme = process_theme(theme)  # Implement this function
            return render_template('theme.html', theme=processed_theme)
        
        elif 'proceed' in request.form:
            return redirect(url_for('assets'))

    return render_template('theme.html')

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

if __name__ == '__main__':
    app.run(debug=True)
