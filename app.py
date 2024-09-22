from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from keybert import KeyBERT
from diffusers import AutoPipelineForText2Image
import torch
import csv
import os
import time
import random
from github_uploader_images import upload_image_to_github
from dotenv import load_dotenv

# Load environment variables (e.g. for a GitHub token)

load_dotenv()

# Initializing Flask application and database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
db = SQLAlchemy(app)

# A database model for storing image data


class ImageData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    keywords = db.Column(db.String(500), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(100), nullable=False)


# Create database tables
with app.app_context():
    db.create_all()

# Initializing KeyBERT
kw_model = KeyBERT()

# Initializing the SDXL model for image generation
pipe = AutoPipelineForText2Image.from_pretrained(
    "stabilityai/sdxl-turbo", torch_dtype=torch.float16, variant="fp16")
pipe.to("cuda")

# Function for generating a unique header using KeyBERT (2-3 words)

# Global list for storing already generated headers
generated_titles = []


def generate_unique_title(input_text):
    # Extract key phrases of 2 to 3 words (bigrams and trigrams)
    keywords = kw_model.extract_keywords(
        input_text, keyphrase_ngram_range=(2, 3), stop_words='english', top_n=20)

    # Sort key phrases by relevance (already sorted in KeyBERT)
    sorted_keywords = sorted(keywords, key=lambda x: x[1], reverse=True)
    # Generate a random unique header
    if sorted_keywords:
        # Trying to find a unique headline
        attempts = 0  # Limit the number of attempts to avoid an infinite loop
        while attempts < 10:
            random_title = random.choice(
                [kw[0] for kw in sorted_keywords]).title()
            if random_title not in generated_titles:
                # If the header is unique, add it to the list and return it
                generated_titles.append(random_title)
                return random_title
            attempts += 1

    return "Untitled"


# Function for generating unique keywords using KeyBERT


def generate_unique_keywords(input_text):
    keywords = kw_model.extract_keywords(
        input_text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=20)
    unique_keywords = list(
        set([kw[0] for kw in keywords]))  # Removing duplicates
    random_keywords = random.sample(unique_keywords, min(
        10, len(unique_keywords)))  # Randomize up to 10 keywords
    return ', '.join(random_keywords)

# Image generation function with SDXL


def generate_image(title, keywords, id):
    # Form prompt from title and keywords
    prompt = f"{title}, {keywords}"
    image = pipe(prompt=prompt, num_inference_steps=1,
                 guidance_scale=0.0).images[0]
    timestamp = int(time.time())  # Get the current time in seconds
    filename = f"{id}_{timestamp}.png"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(image_path)
    return filename

# Home page with a form for generating images


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        num_images = int(request.form['num_images'])
        input_prompt = request.form['input_prompt']  # User Prompt

        for i in range(1, num_images + 1):
            # Generation of unique title and keywords
            generated_title = generate_unique_title(input_prompt)
            keywords = generate_unique_keywords(input_prompt)

            # Image generation
            image_filename = generate_image(generated_title, keywords, i)

            # Saving data to the database
            new_image = ImageData(
                title=generated_title,
                keywords=keywords,
                prompt=f"{generated_title}, {keywords}",
                image_filename=image_filename
            )
            db.session.add(new_image)
            db.session.commit()

        return redirect(url_for('gallery'))

    return render_template('index.html')

# Image gallery page


@app.route('/gallery')
def gallery():
    images = ImageData.query.all()
    return render_template('gallery.html', images=images)

# Function for saving data to CSV and uploading images to GitHub


@app.route('/save_to_csv', methods=['POST'])
def save_to_csv():
    pinterest_board = request.form['pinterest_board']
    upload_to_github = request.form.get(
        'upload_to_github')  # Check the status of the checkbox
    images = ImageData.query.all()

    # Get the current timestamp
    unix_timestamp = int(time.time())
    # Create a file name based on the timestamp
    filename = f'report/images_data_{unix_timestamp}.csv'

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'Media URL', 'Pinterest board', 'Keywords'])

        for image in images:
            image_url = ''
            # If the checkbox is activated, upload the image to GitHub
            if upload_to_github:
                try:
                    local_image_path = os.path.join(
                        app.config['UPLOAD_FOLDER'], image.image_filename)
                    image_url = upload_image_to_github(
                        local_image_path, image.image_filename)
                    time.sleep(1)
                except Exception as e:
                    print(f"Error upload image GitHub: {str(e)}")

            # Writing data to CSV
            writer.writerow(
                [image.title, image_url, pinterest_board, image.keywords])

    return f'Data saved successfully to {filename}!'


if __name__ == '__main__':
    app.run(debug=True)
