import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger


FILE_PATH = "data/raw/phisingData.csv"
DATABASE_NAME = "network_security"
COLLECTION_NAME = "network_logs"


def get_mongodb_client() -> MongoClient:
    try:
        load_dotenv()

        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI is not set in the .env file")

        client = MongoClient(mongo_uri, server_api=ServerApi("1"))
        client.admin.command("ping")
        logger.info("Connected to MongoDB successfully")

        return client
    except Exception as error:
        logger.error("MongoDB connection failed", exc_info=True)
        raise NetworkSecurityException(error, sys)


def read_csv_file(file_path: str) -> pd.DataFrame:
    try:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        if path.suffix.lower() != ".csv":
            raise ValueError(f"Expected a CSV file, got: {path.suffix}")

        dataframe = pd.read_csv(path)
        logger.info("Loaded CSV file: %s with shape: %s", path, dataframe.shape)

        return dataframe
    except Exception as error:
        logger.error("Failed to read CSV file: %s", file_path, exc_info=True)
        raise NetworkSecurityException(error, sys)


def push_dataframe_to_mongodb(
    dataframe: pd.DataFrame,
    database_name: str,
    collection_name: str,
) -> int:
    client = None

    try:
        if dataframe.empty:
            logger.warning("CSV file is empty. No records pushed to MongoDB")
            return 0

        dataframe = dataframe.where(pd.notnull(dataframe), None)
        records = dataframe.to_dict(orient="records")

        client = get_mongodb_client()
        collection = client[database_name][collection_name]

        result = collection.insert_many(records)
        inserted_count = len(result.inserted_ids)

        logger.info(
            "Inserted %s records into MongoDB database=%s collection=%s",
            inserted_count,
            database_name,
            collection_name,
        )

        return inserted_count
    except Exception as error:
        logger.error("Failed to insert records into MongoDB", exc_info=True)
        raise NetworkSecurityException(error, sys)
    finally:
        if client is not None:
            client.close()
            logger.info("MongoDB connection closed")


def main() -> None:
    try:
        dataframe = read_csv_file(FILE_PATH)
        inserted_count = push_dataframe_to_mongodb(
            dataframe=dataframe,
            database_name=DATABASE_NAME,
            collection_name=COLLECTION_NAME,
        )
        print(f"Inserted {inserted_count} records into MongoDB")
    except Exception as error:
        logger.error("Failed to push data to MongoDB", exc_info=True)
        if isinstance(error, NetworkSecurityException):
            raise
        raise NetworkSecurityException(error, sys)


if __name__ == "__main__":
    main()
