import os
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI ni najden/ga ni brat")

client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
db = client[MONGODB_DB]


def get_db():
    return db
