import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from networksecurity.constants import (
    CONFIG_FILE_PATH,
    MODEL_CONFIG_FILE_PATH,
    SCHEMA_FILE_PATH,
)
from networksecurity.entity.artifact_entity import (
    DataTransformationArtifact,
    ModelTrainerArtifact,
)
from networksecurity.entity.config_entity import ModelTrainerConfig
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.utils.main_utils import read_yaml_file
from networksecurity.utils.ml_utils import save_object


class ModelTrainer:
    def __init__(
        self,
        data_transformation_artifact: DataTransformationArtifact | None = None,
        model_trainer_config: ModelTrainerConfig | None = None,
    ) -> None:
        try:
            self.data_transformation_artifact = data_transformation_artifact
            self.model_trainer_config = (
                model_trainer_config or self.get_model_trainer_config()
            )
        except Exception as error:
            logger.error("Failed to initialize ModelTrainer", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def get_model_trainer_config() -> ModelTrainerConfig:
        try:
            config = read_yaml_file(CONFIG_FILE_PATH)
            training_config = config["model_training"]
            transformation_config = config["data_transformation"]

            return ModelTrainerConfig(
                transformed_train_path=transformation_config["transformed_train_path"],
                transformed_test_path=transformation_config["transformed_test_path"],
                schema_path=SCHEMA_FILE_PATH,
                model_config_path=MODEL_CONFIG_FILE_PATH,
                trained_model_path=training_config["trained_model_path"],
            )
        except Exception as error:
            logger.error("Failed to read model trainer configuration", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def _get_transformed_paths(self) -> tuple[str, str]:
        if self.data_transformation_artifact is not None:
            return (
                self.data_transformation_artifact.transformed_train_path,
                self.data_transformation_artifact.transformed_test_path,
            )

        return (
            self.model_trainer_config.transformed_train_path,
            self.model_trainer_config.transformed_test_path,
        )

    @staticmethod
    def read_dataframe(file_path: str) -> pd.DataFrame:
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"Data file not found: {path}")

            dataframe = pd.read_csv(path)
            logger.info("Loaded data file: %s with shape: %s", path, dataframe.shape)

            return dataframe
        except Exception as error:
            logger.error("Failed to read data file: %s", file_path, exc_info=True)
            raise NetworkSecurityException(error, sys)

    def separate_features_and_target(
        self,
        dataframe: pd.DataFrame,
        schema: dict,
    ) -> tuple[pd.DataFrame, pd.Series]:
        try:
            target_column = schema["target_column"]
            feature_columns = list(schema["columns"].keys())

            if target_column not in dataframe.columns:
                raise ValueError(f"Target column not found: {target_column}")

            missing_features = [
                column for column in feature_columns if column not in dataframe.columns
            ]
            if missing_features:
                raise ValueError(f"Feature columns not found: {missing_features}")

            features = dataframe[feature_columns]
            target = dataframe[target_column]

            logger.info(
                "Prepared training data: features=%s target=%s",
                features.shape,
                target.shape,
            )

            return features, target
        except Exception as error:
            logger.error("Failed to separate features and target", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def get_model(model_name: str, params: dict) -> object:
        try:
            if model_name == "random_forest":
                return RandomForestClassifier(**params)

            if model_name == "xgboost":
                from xgboost import XGBClassifier

                return XGBClassifier(**params)

            raise ValueError(f"Unsupported model: {model_name}")
        except Exception as error:
            logger.error("Failed to initialize model: %s", model_name, exc_info=True)
            raise NetworkSecurityException(error, sys)

    def train_model(
        self,
        train_features: pd.DataFrame,
        train_target: pd.Series,
    ) -> object:
        try:
            model_config = read_yaml_file(self.model_trainer_config.model_config_path)
            model_name = model_config["model"]["name"]
            model_params = model_config["model"]["params"]

            model = self.get_model(model_name, model_params)
            model.fit(train_features, train_target)

            logger.info("Model training completed: model=%s", model_name)
            return model
        except Exception as error:
            logger.error("Model training failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def save_trained_model(self, model: object) -> str:
        try:
            trained_model_path = self.model_trainer_config.trained_model_path
            save_object(trained_model_path, model)
            logger.info("Saved trained model to %s", trained_model_path)
            return trained_model_path
        except Exception as error:
            logger.error("Failed to save trained model", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def initiate_model_training(self) -> ModelTrainerArtifact:
        try:
            logger.info("Model training started")

            transformed_train_path, transformed_test_path = self._get_transformed_paths()
            schema = read_yaml_file(self.model_trainer_config.schema_path)

            train_dataframe = self.read_dataframe(transformed_train_path)
            if train_dataframe.empty:
                raise ValueError("Transformed train dataframe is empty")

            train_features, train_target = self.separate_features_and_target(
                train_dataframe,
                schema,
            )

            trained_model = self.train_model(train_features, train_target)
            trained_model_path = self.save_trained_model(trained_model)

            model_trainer_artifact = ModelTrainerArtifact(
                trained_model_path=trained_model_path,
                transformed_train_path=transformed_train_path,
                transformed_test_path=transformed_test_path,
            )

            logger.info("Model training completed: %s", model_trainer_artifact)
            return model_trainer_artifact
        except Exception as error:
            logger.error("Model training pipeline failed", exc_info=True)
            raise NetworkSecurityException(error, sys)
