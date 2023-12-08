# encode.py
import datetime
import jwt # import jwt library

SECRET_KEY = "python_jwt"

def encode(data):
    # encode the data with SECRET_KEY and
    # algorithm "HS256" -> Symmetric Algorithm
    encode_data = jwt.encode(payload=data, \
                             key=SECRET_KEY, algorithm="HS256")
    print(encode_data)
    return encode_data

def decode(data):
    # decode the data with SECRET_KEY and
    # algorithm "HS256" -> Symmetric Algorithm
    decode_data = jwt.decode(jwt=data, key=SECRET_KEY, \
                             algorithms="HS256")
    print(decode_data)
    return decode_data
