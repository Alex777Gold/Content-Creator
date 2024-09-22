import pytest
from app import app, db, ImageData, generate_unique_title, generate_unique_keywords, generate_image, save_to_csv
from flask import url_for
from unittest.mock import patch, MagicMock
import os
import tempfile
import time
import csv

# Fixtura for testing the Flask application


@pytest.fixture
def client():
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['TESTING'] = True

    # Create a test application client
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

    # Closing and deleting the temporary database after tests
    os.close(db_fd)
    os.unlink(db_path)

# Testing the home page (GET)


def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Generate Image' in response.data

# Testing the image gallery


def test_gallery_page(client):
    with app.app_context():
        image = ImageData(title="Test Image", keywords="keyword1, keyword2",
                          prompt="Test Prompt", image_filename="test_image.png")
        db.session.add(image)
        db.session.commit()

    response = client.get('/gallery')
    assert response.status_code == 200
    assert b'Test Image' in response.data

# Testing the unique header generation function


@patch('app.kw_model.extract_keywords')
def test_generate_unique_title(mock_extract_keywords):
    mock_extract_keywords.return_value = [("test title", 0.9)]
    title = generate_unique_title("test input")
    assert title == "Test Title"

# Testing the unique keyword generation function


@patch('app.kw_model.extract_keywords')
def test_generate_unique_keywords(mock_extract_keywords):
    mock_extract_keywords.return_value = [("keyword1", 0.9), ("keyword2", 0.8)]
    keywords = generate_unique_keywords("test input")
    assert "keyword1" in keywords
    assert "keyword2" in keywords

# Testing the image generation function


@patch('app.pipe')
def test_generate_image(mock_pipe):
    mock_image = MagicMock()
    mock_pipe.return_value.images = [mock_image]
    mock_image.save = MagicMock()

    filename = generate_image("Test Title", "Test Keywords", 1)
    assert filename.endswith('.png')
    mock_image.save.assert_called_once()

# Testing the CSV file testing function


def test_csv_file(client):
    # Create test data
    with app.app_context():
        image = ImageData(title="Test Image", keywords="keyword1, keyword2",
                          prompt="Test Prompt", image_filename="test_image.png")
        db.session.add(image)
        db.session.commit()

    # Call the save to CSV function
    response = client.post('/save_to_csv', data={
        'pinterest_board': 'Test Board',
        'upload_to_github': False
    })

    # Checking that the file has been created
    csv_filename = 'report/images_data_{}.csv'.format(int(time.time()))
    assert os.path.exists(csv_filename)

    # Check the contents of the CSV file
    with open(csv_filename, mode='r', newline='') as file:
        reader = csv.reader(file)
        header = next(reader)
        assert header == ['Title', 'Media URL', 'Pinterest board', 'Keywords']

        row = next(reader)
        assert row[0] == "Test Image"
        assert row[2] == "Test Board"
        assert row[3] == "keyword1, keyword2"

    # Delete the file after checking
    os.remove(csv_filename)
