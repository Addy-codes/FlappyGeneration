from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient

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

def process_theme(theme):
    # Add your theme processing logic here
    return theme  # Example: return the theme as-is

@app.route('/assets')
def assets():
    # Your assets page logic
    return render_template('assets.html')

if __name__ == '__main__':
    app.run(debug=True)
