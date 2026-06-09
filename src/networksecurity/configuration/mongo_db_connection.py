import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi


load_dotenv()


class MongoDBConnection:
    def __init__(self) -> None:
        self.mongo_db_url = os.getenv("MONGODB_URI")
        if not self.mongo_db_url:
            raise ValueError("MONGODB_URI is not set in environment variables")

    def get_client(self) -> MongoClient:
        return MongoClient(self.mongo_db_url, server_api=ServerApi("1"))
