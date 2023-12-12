import certifi
from pymongo import MongoClient

import config

uri = f"mongodb+srv://{config.mongodb_username}:{config.mongodb_password}@{config.mongodb_database}.ot7o9de.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client.sample

from bson.json_util import dumps

change_stream = db.posts.watch()
for change in change_stream:
    print(dumps(change))
    print('') # for readability only