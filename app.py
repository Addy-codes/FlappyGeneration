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
import helper
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

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        print("Starting to add to MongoDB")
        
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
        print("Going to game theme")
        return redirect(url_for('gameTheme'))

    return render_template('login.html')

@app.route('/gameTheme', methods=['GET', 'POST'])
def gameTheme():
    print("In game theme")
    if request.method == 'POST':
        if 'generate' in request.form:
            theme = request.form.get('theme')
            print("Finding choice")
            game_choice = helper.choice(theme)  # Assume this returns 'flappy' or 'wackamole'
            print(game_choice)
            # Common code for saving theme to MongoDB
            microservice_url = f"{DB_BASE_URL}/addtheme"
            user = session.get('user_info')
            data = {'theme': theme, 'user': user['userId']}
            headers = {'Content-Type': 'application/json'}
            outputId = None
            try:
                response = requests.post(microservice_url, json=data, headers=headers)
                if response.status_code == 200:
                    print('Successfully Added In Db')
                    outputId = response.json().get('outputId')
                else:
                    print('Error While Adding In Db')
                    print(response)
            except Exception as e:
                print(f"Error: {e}")

            if game_choice == 'flappy':
                # Flappy Bird specific processing
                prompt = f"""
                    Given the theme '{theme}' for a Flappy Bird game, please provide ideas for the following elements, keep it short:
                    1. Obstacle 1: This should represent something or someone the main character needs to avoid in the game environment, this obstacle is something that is preferably in the sky and would replace the top pipe.
                    2. Obstacle 2: Another element in the game that poses a challenge to the main character that is preferably on the ground.
                    3. Main Character: A representation of the main theme in a creative and thematic way.
                    4. Background Image: A scene that sets the environment where the action takes place.
                    """
                processed_theme = helper.process_theme(prompt)
                parsed_theme = helper.parse_processed_theme_flappy(processed_theme)
                session['processed_theme'] = parsed_theme
                session['outputId'] = outputId
                return render_template('modifyflappytheme.html', processed_theme=parsed_theme)
            
            elif game_choice == 'wackamole':
                # Whack-a-Mole specific processing
                prompt = f"""
                Given the theme '{theme}' for a Whack-a-Mole game, please provide creative ideas for the following elements, make sure the elements follow the theme, keep the description short and precise:
                1. Mole: A character or element that players will try to catch, find, or 'whack'.
                2. Hole: A representation of where this character or element can hide.
                3. Background Image: A visually rich scene that encapsulates the essence of '{theme}', providing an immersive backdrop for the game.
                """
                processed_theme = helper.process_theme(prompt)
                parsed_theme = helper.parse_processed_theme_wackamole(processed_theme)
                session['processed_theme'] = parsed_theme
                session['outputId'] = outputId
                return render_template('modifywackamoletheme.html', processed_theme=parsed_theme)

    return render_template('theme.html')

@app.route('/modifyflappytheme', methods=['GET', 'POST'])   
def modify_flappy_theme():
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

        helper.generate_flappyassets(main_character, game_background, top_obstacle, bottom_obstacle)
        # For example, redirecting to another page with this data
        return redirect(url_for('assets'))  # Replace 'next_page' with your next page

    # Retrieve parsed processed theme from session
    processed_theme = session.get('processed_theme', {})
    return render_template('modifyflappytheme.html', processed_theme=processed_theme)

@app.route('/modifywackamoletheme', methods=['GET', 'POST'])   
def modify_wackamole_theme():
    if request.method == 'POST':
        mole = request.form.get('mole')
        hole = request.form.get('hole')
        game_background = request.form.get('game_background')

        # Store parameters in the session
        session['mole'] = mole
        session['hole'] = hole
        session['game_background'] = game_background
        print("ajnajsncsjnvjnadjnvmsjdnfsjnvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        # Here, you could call a helper function to generate assets for the game
        helper.generate_wackamoleassets(mole, hole, game_background)
        # Redirect to a page to showcase or utilize the generated assets
        return redirect(url_for('wackamole_assets'))  # Replace 'wackamole_assets' with the appropriate route

    # Retrieve parsed processed theme from session
    processed_theme = session.get('processed_theme', {})
    return render_template('modifywackamoletheme.html', processed_theme=processed_theme)

@app.route('/wackamole_assets', methods=['GET', 'POST'])
def wackamole_assets():
    if request.method == 'POST':
        folder_path = './CustomWackAMole'
        zip_path = 'WackAMole_website.zip'

        # Zip the website folder
        helper.zip_folder(folder_path, zip_path)

        # Deploy the site
        deploy_response = helper.deploy_site(zip_path)
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
    
    return render_template('wackamole_assets.html')

@app.route('/assets', methods=['GET', 'POST'])
def assets():
    if request.method == 'POST':
        folder_path = './CustomFlappy'
        zip_path = 'website.zip'

        # Zip the website folder
        helper.zip_folder(folder_path, zip_path)

        # Deploy the site
        deploy_response = helper.deploy_site(zip_path)
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
    helper.generate_bird(main_character, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/top_obstacle', methods=['POST'])
def regenerate_top_obstacle():
    out_dir = "./CustomFlappy/img"
    top_obstacle = session.get('top_obstacle', '')
    helper.generate_top_pipe(top_obstacle, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/bottom_obstacle', methods=['POST'])
def regenerate_bottom_obstacle():
    out_dir = "./CustomFlappy/img"
    bottom_obstacle = session.get('bottom_obstacle', '')
    helper.generate_bot_pipe(bottom_obstacle, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/background', methods=['POST'])
def regenerate_background():
    out_dir = "./CustomFlappy/img"
    background_image = session.get('game_background', '')
    helper.generate_background(background_image, out_dir)
    return redirect(url_for('assets'))

@app.route('/regenerate/mole', methods=['POST'])
def regenerate_mole():
    print(f"Generating {session.get('mole')}")
    helper.generate_bird(f"Face of {session.get('mole')}", f"./CustomWackAMole/css/mole.png", 'static/mole.png', (346, 413))
    helper.remove_background(f"./CustomWackAMole/css/mole.png")
    return redirect(url_for('wackamole_assets'))

@app.route('/regenerate/hole', methods=['POST'])
def regenerate_hole():
    print(f"Generating {session.get('hole')}")
    helper.generate_bird(f"{session.get('hole')}", f"./CustomWackAMole/css/hole.png", 'static/hole.png', (210, 76))
    helper.remove_background(f"./CustomWackAMole/css/hole.png")
    return redirect(url_for('wackamole_assets'))

@app.route('/regenerate/wackamolebackground', methods=['POST'])
def regenerate_wackamolebackground():
    print(f"Generating {session.get('game_background')}")
    helper.generate_bird(f"{session.get('game_background')}", f"./CustomWackAMole/css/background.png", 'static/background.png', (1920, 1080))
    return redirect(url_for('wackamole_assets'))


if __name__ == '__main__':
    app.run(debug=True)
