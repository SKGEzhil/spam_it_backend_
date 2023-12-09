import boto3, botocore
import certifi
from botocore.config import Config
from flask import Flask, request, jsonify
from passlib.hash import sha256_crypt
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.utils import secure_filename
from datetime import date
import token_encryption
from bson import json_util
from flask_cors import CORS
import os
import config

uri = f"mongodb+srv://{config.mongodb_username}:{config.mongodb_password}@{config.mongodb_database}.ot7o9de.mongodb.net/?retryWrites=true&w=majority"


client = MongoClient(uri, tlsCAFile=certifi.where())


try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client.sample

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


s3 = boto3.client('s3',
                  aws_access_key_id=f'{config.aws_access_key_id}',
                  aws_secret_access_key= f'{config.aws_secret_access_key}',
                  config=Config(signature_version='s3v4')
                  )

BUCKET_NAME='losties'

base_dir = os.getcwd()

# get username
@app.route('/get_username', methods=['POST'])
def getUsername():
    json = request.json
    roll_no = json['roll_no']
    name = db.users.find_one({'roll_no': roll_no})['name']
    return name

@app.route('/add_reply', methods=['POST'])
def addReply():
    json = request.json
    roll_no = json['roll_no']
    reply = json['reply']
    post_id = json['post_id']
    name = db.users.find_one({'roll_no': roll_no})['name']
    db.replies.insert_one({'roll_no': roll_no, 'name': name,'reply': reply, 'post_id': post_id})
    return 'Reply success'

# Get replies for a post
@app.route('/get_replies', methods=['POST'])
def getReplies():
    json = request.json
    post_id = json['post_id']
    replies = list(db.replies.find({'post_id': post_id}))
    replies_json = json_util.dumps(replies)
    return replies_json

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return {'error': 'No file part'}, 400

    image = request.files['image']
    if image.filename == '':
        return {'error': 'No selected file'}, 400

    filename = secure_filename(image.filename)
    image.save(filename)
    s3.upload_file(
        Bucket = BUCKET_NAME,
        Filename=filename,
        Key = filename
    )

    download_link = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
    print(download_link)
    return download_link

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/register', methods=['POST'])
def register():
    json = request.json
    roll_no = json['roll_no']
    name = json['name']
    email = json['email']
    password = json['password']
    existing_user = db.users.find_one({'roll_no': roll_no})
    if existing_user is None:
        pwd_hash = sha256_crypt.encrypt(password)
        db.users.insert_one({'roll_no': roll_no, 'name': name, 'email': email, 'password': pwd_hash})
        token = token_encryption.encode({'roll_no': roll_no, 'password': password})
        return token
    else:
        return 'User already exists'
    return 'Registration successful'

@app.route('/login', methods=['POST'])
def login():
    json = request.json
    roll_no = json['roll_no']
    password = json['password']
    user = db.users.find_one({'roll_no': roll_no})
    if user is None:
        print('User not found')
        return 'no_user'
    else:
        pwd_hash = user.get('password', '')
        if sha256_crypt.verify(password, pwd_hash):
            print(id)
            token = token_encryption.encode(json)
            print(token)
            data = token_encryption.decode(token)
            print(data['roll_no'])
            return 'success'
        else:
            print('incorrect')
            return 'incorrect'
    return 'login Successfull'

@app.route('/create_post', methods=['POST'])
def createPost():

    today = date.today()

    json = request.json
    roll_no = json['roll_no']
    subject = json['subject']
    content = json['content']
    image = json['image']
    name = db.users.find_one({'roll_no': roll_no})['name']
    db.posts.insert_one({'roll_no': roll_no, 'name': name, 'subject': subject, 'content': content, 'image': image, 'replies': [], 'date':today.strftime("%d/%m/%Y")})
    return 'success'

@app.route('/get_posts', methods=['GET'])
def getPosts():
    posts = list(db.posts.find())
    posts_json = json_util.dumps(posts)
    return posts_json

@app.route('/reply', methods=['GET'])
def reply():
    json = request.json
    roll_no = json['roll_no']
    name = json['name']
    body = json['body']
    db.replies.insert_one({'id': id, 'roll_no': roll_no, 'name': name, 'body': body})
    return 'Reply'


if __name__ == '__main__':
    app.run(degug=True)
