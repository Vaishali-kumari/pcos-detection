from flask import Flask
from pymongo import MongoClient

app = Flask(__name__)
app.config.from_pyfile('../config.py')

# Initialize MongoDB
client = MongoClient(app.config['MONGO_URI'])
db = client.pcos_prediction

# Import routes after app is created to avoid circular imports
from app import routes