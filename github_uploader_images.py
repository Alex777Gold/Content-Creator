import requests
import base64
import os

# Get the token from the environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
OWNER = 'name gitgub account'
REPO = 'repository name'
BRANCH = 'branch name'


def upload_image_to_github(file_path, image_name):
    # GITHUB_TOKEN environment variable is set
    if not GITHUB_TOKEN:
        raise EnvironmentError("Enviroment GITHUB_TOKEN not install.")

    # Reading the image file
    with open(file_path, 'rb') as file:
        image_content = file.read()

    # Encoding the file content in base64
    image_base64 = base64.b64encode(image_content).decode('utf-8')

    # Create URL for file download
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{image_name}"

    # Generating data for the query
    data = {
        "message": f"Upload image {image_name}",
        "content": image_base64,
        "branch": BRANCH
    }

    # Headers for authentication
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    # Send a PUT request to the GitHub API
    response = requests.put(url, headers=headers, json=data)

    # Checking the status of the response
    if response.status_code == 201:
        # Form a link to the raw version of the image
        raw_url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{image_name}"
        print(f"Image {image_name} secsessful upload on GitHub")
        return raw_url
    else:
        raise Exception(f"Error upload image on GitHub: {response.json()}")
