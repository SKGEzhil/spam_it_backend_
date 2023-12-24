import boto3
import certifi
from botocore.config import Config
from flask import Flask, request
from passlib.hash import sha256_crypt
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from datetime import date
import token_encryption
from bson import json_util, ObjectId
from flask_cors import CORS
import os
import config
import firebase_admin
from firebase_admin import credentials, messaging
import json as pyjson



# Firebase admin sdk
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)


# MongoDB connection
uri = f"mongodb+srv://{config.mongodb_username}:{config.mongodb_password}@{config.mongodb_database}.ot7o9de.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, tlsCAFile=certifi.where())
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client.sample

# Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# S3 connection
s3 = boto3.client('s3',
                  aws_access_key_id=f'{config.aws_access_key_id}',
                  aws_secret_access_key= f'{config.aws_secret_access_key}',
                  config=Config(signature_version='s3v4')
                  )
BUCKET_NAME='losties'
base_dir = os.getcwd()


# opened post
@app.route('/set_opened', methods=['POST'])
def setOpened():
    json = request.json
    post_id = json['post_id']
    roll_no = json['roll_no']

    print(post_id)
    print(roll_no)

    opened_posts = db.opened.find_one({'roll_no': roll_no})['posts']
    print(opened_posts)
    opened_posts.append(post_id)

    db.opened.update_one({'roll_no': roll_no}, {'$set': {'posts': opened_posts}})
    return 'success'

# get opened post
@app.route('/get_opened', methods=['POST'])
def getOpened():
    json = request.json
    roll_no = json['roll_no']
    opened_posts = list(db.opened.find_one({'roll_no': roll_no})['posts'])
    opened_post_json = json_util.dumps(opened_posts)
    return opened_post_json

# send fcm notification
@app.route('/send_notification', methods=['GET'])
def sendNotification(name, body):
    # The topic name can be optionally prefixed with "/topics/".
    topic = 'topic'

    # See documentation on defining a message payload.
    message = messaging.Message(
        data={
            'name': name,
            'body': body,
        },
        topic=topic,
    )

    # Send a message to the devices subscribed to the provided topic.
    response = messaging.send(message)
    # Response is a message ID string.
    print('Successfully sent message:', response)
    return 'success'

# send reply notification
def sendReplyNotification(tokens, name, reply):
    # Create a list containing up to 500 registration tokens.
    # These registration tokens come from the client FCM SDKs.
    registration_tokens = tokens

    message = messaging.MulticastMessage(
        data={'name': f'{name} has replied to your post', 'body': f'{reply}'},
        tokens=registration_tokens,
    )
    response = messaging.send_multicast(message)
    # See the BatchResponse reference documentation
    # for the contents of response.
    print('{0} messages were sent successfully'.format(response.success_count))

@app.route('/token_auth', methods=['POST'])
def tokenAuth():
    json = request.json
    token = json['token']
    data = token_encryption.decode(token)
    roll_no = data['roll_no']
    password = data['password']
    user = db.users.find_one({'roll_no': roll_no})
    if user is None:
        print('User not found')
        return 'no_user'
    else:
        pwd_hash = user.get('password', '')
        if sha256_crypt.verify(password, pwd_hash):
            print(data['roll_no'])
            return 'success'
        else:
            print('incorrect')
            return 'incorrect'

# generate token
@app.route('/generate_token', methods=['POST'])
def generateToken():
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
            return token
        else:
            print('incorrect')
            return 'incorrect'

# get username
@app.route('/get_username', methods=['POST'])
def getUsername():
    json = request.json
    roll_no = json['roll_no']
    name = db.users.find_one({'roll_no': roll_no})['name']
    return name

@app.route('/add_reply', methods=['POST'])
def addReply():

    today = date.today()

    json = request.json
    roll_no = json['roll_no']
    reply = json['reply']
    post_id = json['post_id']
    name = db.users.find_one({'roll_no': roll_no})['name']
    db.replies.insert_one({'roll_no': roll_no, 'name': name,'reply': reply, 'post_id': post_id, 'date':today.strftime("%d %b")})

    roll_no_creator = db.posts.find_one({'_id': ObjectId(post_id)})['roll_no']
    name_creator = db.users.find_one({'roll_no': roll_no_creator})['name']
    fcm_token_list = db.users.find_one({'roll_no': roll_no_creator})['fcm_token']
    sendReplyNotification(fcm_token_list, name_creator, reply)

    return 'Reply success'

# Get replies for a post
@app.route('/get_replies', methods=['POST'])
def getReplies():
    json = request.json
    post_id = json['post_id']
    replies = list(db.replies.find({'post_id': post_id}).sort({ '_id': -1 }))
    replies_json = json_util.dumps(replies)
    return replies_json

@app.route('/get_all_replies', methods=['POST'])
def getAllReplies():
    json = request.json
    roll_no = json['roll_no']
    all_posts = [str(post['_id']) for post in db.posts.find({'roll_no': roll_no})]
    all_replies = []
    for post_id in all_posts:
        replies = list(db.replies.find({'post_id': post_id}).sort({ '_id': -1 }))
        all_replies.extend(replies)
    replies_json = json_util.dumps(all_replies)
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
    os.remove(filename)

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
    fcm_token = json['fcm_token']
    existing_user = db.users.find_one({'roll_no': roll_no})

    fcm_token_list = [fcm_token]

    if existing_user is None:
        pwd_hash = sha256_crypt.encrypt(password)
        db.users.insert_one({'roll_no': roll_no, 'name': name, 'email': email, 'password': pwd_hash, 'fcm_token': fcm_token_list})
        db.opened.insert_one({'roll_no': roll_no, 'posts': []})
        token = token_encryption.encode({'roll_no': roll_no, 'password': password})
        return token
    else:
        return 'failed'

@app.route('/login', methods=['POST'])
def login():
    json = request.json
    roll_no = json['roll_no']
    password = json['password']
    fcm_token = json['fcm_token']
    user = db.users.find_one({'roll_no': roll_no})
    if user is None:
        print('User not found')
        return 'failed'
    else:
        pwd_hash = user.get('password', '')
        if sha256_crypt.verify(password, pwd_hash):

            fcm_token_list = db.users.find_one({'roll_no': roll_no})['fcm_token']
            fcm_token_list.append(fcm_token)

            db.users.update_one({'roll_no': roll_no}, {'$set': {'fcm_token': fcm_token_list}})
            print(id)
            token = token_encryption.encode(json)
            print(token)
            return token
        else:
            print('incorrect')
            return 'failed'

@app.route('/create_post', methods=['POST'])
def createPost():

    today = date.today()

    json = request.json
    roll_no = json['roll_no']
    subject = json['subject']
    content = json['content']
    image = json['image']
    tags = json['tags']
    cab_details = json['cab']

    # cabDetails = pyjson.loads(cab_details)

    tagList = []

    for tag in tags:
        tagList.append(tag)

    name = db.users.find_one({'roll_no': roll_no})['name']
    db.posts.insert_one({'roll_no': roll_no, 'name': name, 'subject': subject, 'content': content, 'image': image, 'tags': tagList, 'cab': cab_details, 'date':today.strftime("%d %b")})

    sendNotification(name, subject)

    return 'success'

@app.route('/get_posts', methods=['GET'])
def getPosts():
    posts = list(db.posts.find().sort({ '_id': -1 }))
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
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
