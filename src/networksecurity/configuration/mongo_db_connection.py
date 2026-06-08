import os

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()


class MongoDBConnection:
    def __init__(self) -> None:
        self.mongo_db_url = os.getenv("MONGO_DB_URL")
        if not self.mongo_db_url:
            raise ValueError("MONGO_DB_URL is not set in environment variables")

    def get_client(self) -> MongoClient:
        return MongoClient(self.mongo_db_url)
