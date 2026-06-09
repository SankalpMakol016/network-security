import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from networksecurity.configuration.mongo_db_connection import MongoDBConnection
from networksecurity.entity.artifact_entity import DataIngestionArtifact
from networksecurity.entity.config_entity import DataIngestionConfig
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.utils.main_utils import read_yaml_file


class DataIngestion:
    def __init__(self, data_ingestion_config: DataIngestionConfig | None = None) -> None:
        try:
            self.data_ingestion_config = data_ingestion_config or self.get_data_ingestion_config()
        except Exception as error:
            logger.error("Failed to initialize DataIngestion", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def get_data_ingestion_config() -> DataIngestionConfig:
        try:
            config = read_yaml_file("config/config.yaml")

            return DataIngestionConfig(
                database_name=config["database"]["name"],
                collection_name=config["database"]["collection"],
                raw_data_path=config["paths"]["raw_data"],
                train_data_path=config["paths"]["train_data"],
                test_data_path=config["paths"]["test_data"],
                test_size=config["data_ingestion"]["test_size"],
            )
        except Exception as error:
            logger.error("Failed to read data ingestion configuration", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def export_collection_as_dataframe(self) -> pd.DataFrame:
        try:
            database_name = self.data_ingestion_config.database_name
            collection_name = self.data_ingestion_config.collection_name

            logger.info(
                "Exporting MongoDB collection to dataframe: database=%s collection=%s",
                database_name,
                collection_name,
            )

            client = MongoDBConnection().get_client()
            collection = client[database_name][collection_name]
            records = list(collection.find())

            if not records:
                logger.warning(
                    "No records found in MongoDB collection: database=%s collection=%s",
                    database_name,
                    collection_name,
                )
                return pd.DataFrame()

            dataframe = pd.DataFrame(records)

            if "_id" in dataframe.columns:
                dataframe.drop(columns=["_id"], inplace=True)

            logger.info("Exported dataframe shape: %s", dataframe.shape)
            return dataframe
        except Exception as error:
            logger.error("Failed to export MongoDB collection as dataframe", exc_info=True)
            raise NetworkSecurityException(error, sys)
        finally:
            if "client" in locals():
                client.close()
                logger.info("MongoDB connection closed")

    def export_data_into_feature_store(self, dataframe: pd.DataFrame) -> str:
        try:
            raw_data_path = Path(self.data_ingestion_config.raw_data_path)
            raw_data_path.parent.mkdir(parents=True, exist_ok=True)

            dataframe.to_csv(raw_data_path, index=False, header=True)
            logger.info("Saved raw data to feature store: %s", raw_data_path)

            return str(raw_data_path)
        except Exception as error:
            logger.error("Failed to save raw data to feature store", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def split_data_as_train_test(self, dataframe: pd.DataFrame) -> tuple[str, str]:
        try:
            train_data_path = Path(self.data_ingestion_config.train_data_path)
            test_data_path = Path(self.data_ingestion_config.test_data_path)

            train_data_path.parent.mkdir(parents=True, exist_ok=True)
            test_data_path.parent.mkdir(parents=True, exist_ok=True)

            train_dataframe, test_dataframe = train_test_split(
                dataframe,
                test_size=self.data_ingestion_config.test_size,
                random_state=42,
            )

            train_dataframe.to_csv(train_data_path, index=False, header=True)
            test_dataframe.to_csv(test_data_path, index=False, header=True)

            logger.info(
                "Saved train data to %s and test data to %s",
                train_data_path,
                test_data_path,
            )

            return str(train_data_path), str(test_data_path)
        except Exception as error:
            logger.error("Failed to split data into train and test files", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        try:
            logger.info("Data ingestion started")

            dataframe = self.export_collection_as_dataframe()
            raw_data_path = self.export_data_into_feature_store(dataframe)
            train_data_path, test_data_path = self.split_data_as_train_test(dataframe)

            data_ingestion_artifact = DataIngestionArtifact(
                raw_data_path=raw_data_path,
                train_data_path=train_data_path,
                test_data_path=test_data_path,
            )

            logger.info("Data ingestion completed: %s", data_ingestion_artifact)
            return data_ingestion_artifact
        except Exception as error:
            logger.error("Data ingestion failed", exc_info=True)
            raise NetworkSecurityException(error, sys)
