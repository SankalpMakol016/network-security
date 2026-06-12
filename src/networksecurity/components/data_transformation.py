import sys
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import StandardScaler

from networksecurity.constants import CONFIG_FILE_PATH, SCHEMA_FILE_PATH
from networksecurity.entity.artifact_entity import (
    DataTransformationArtifact,
    DataValidationArtifact,
)
from networksecurity.entity.config_entity import DataTransformationConfig
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.utils.main_utils import read_yaml_file
from networksecurity.utils.ml_utils import save_object


class DataTransformation:
    def __init__(
        self,
        data_validation_artifact: DataValidationArtifact | None = None,
        data_transformation_config: DataTransformationConfig | None = None,
    ) -> None:
        try:
            self.data_validation_artifact = data_validation_artifact
            self.data_transformation_config = (
                data_transformation_config or self.get_data_transformation_config()
            )
        except Exception as error:
            logger.error("Failed to initialize DataTransformation", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def get_data_transformation_config() -> DataTransformationConfig:
        try:
            config = read_yaml_file(CONFIG_FILE_PATH)
            transformation_config = config["data_transformation"]

            return DataTransformationConfig(
                train_data_path=config["paths"]["train_data"],
                test_data_path=config["paths"]["test_data"],
                schema_path=SCHEMA_FILE_PATH,
                transformed_train_path=transformation_config["transformed_train_path"],
                transformed_test_path=transformation_config["transformed_test_path"],
                preprocessor_path=transformation_config["preprocessor_path"],
                apply_smote=transformation_config["apply_smote"],
                smote_random_state=transformation_config["smote_random_state"],
            )
        except Exception as error:
            logger.error("Failed to read data transformation configuration", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def _get_train_test_paths(self) -> tuple[str, str]:
        if self.data_validation_artifact is not None:
            return (
                self.data_validation_artifact.train_data_path,
                self.data_validation_artifact.test_data_path,
            )

        return (
            self.data_transformation_config.train_data_path,
            self.data_transformation_config.test_data_path,
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

            features = dataframe[feature_columns].copy()
            target = dataframe[target_column].copy()

            target = target.map({-1: 0, 1: 1})
            if target.isna().any():
                raise ValueError("Target column contains unsupported class labels")

            logger.info(
                "Separated features and target: features=%s target=%s",
                features.shape,
                target.shape,
            )

            return features, target
        except Exception as error:
            logger.error("Failed to separate features and target", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def get_preprocessor(self) -> StandardScaler:
        return StandardScaler()

    def transform_train_test_data(
        self,
        train_features: pd.DataFrame,
        test_features: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray, StandardScaler]:
        try:
            preprocessor = self.get_preprocessor()

            transformed_train = preprocessor.fit_transform(train_features)
            transformed_test = preprocessor.transform(test_features)

            logger.info(
                "Scaled train and test features: train=%s test=%s",
                transformed_train.shape,
                transformed_test.shape,
            )

            return transformed_train, transformed_test, preprocessor
        except Exception as error:
            logger.error("Failed to transform train and test data", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def apply_smote_resampling(
        self,
        train_features: np.ndarray,
        train_target: pd.Series,
    ) -> tuple[np.ndarray, np.ndarray]:
        try:
            if not self.data_transformation_config.apply_smote:
                logger.info("SMOTE resampling skipped")
                return train_features, train_target.to_numpy()

            smote = SMOTE(
                random_state=self.data_transformation_config.smote_random_state,
            )
            resampled_features, resampled_target = smote.fit_resample(
                train_features,
                train_target,
            )

            logger.info(
                "Applied SMOTE resampling: original=%s resampled=%s",
                train_features.shape,
                resampled_features.shape,
            )

            return resampled_features, resampled_target
        except Exception as error:
            logger.error("Failed to apply SMOTE resampling", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def _build_transformed_dataframe(
        self,
        features: np.ndarray,
        target: np.ndarray,
        feature_columns: list[str],
        target_column: str,
    ) -> pd.DataFrame:
        transformed_dataframe = pd.DataFrame(features, columns=feature_columns)
        transformed_dataframe[target_column] = target
        return transformed_dataframe

    def save_transformed_data(
        self,
        train_dataframe: pd.DataFrame,
        test_dataframe: pd.DataFrame,
    ) -> tuple[str, str]:
        try:
            transformed_train_path = Path(
                self.data_transformation_config.transformed_train_path
            )
            transformed_test_path = Path(
                self.data_transformation_config.transformed_test_path
            )

            transformed_train_path.parent.mkdir(parents=True, exist_ok=True)
            transformed_test_path.parent.mkdir(parents=True, exist_ok=True)

            train_dataframe.to_csv(transformed_train_path, index=False, header=True)
            test_dataframe.to_csv(transformed_test_path, index=False, header=True)

            logger.info(
                "Saved transformed train data to %s and test data to %s",
                transformed_train_path,
                transformed_test_path,
            )

            return str(transformed_train_path), str(transformed_test_path)
        except Exception as error:
            logger.error("Failed to save transformed data", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def save_preprocessor(self, preprocessor: StandardScaler) -> str:
        try:
            preprocessor_path = self.data_transformation_config.preprocessor_path
            save_object(preprocessor_path, preprocessor)
            logger.info("Saved preprocessor to %s", preprocessor_path)
            return preprocessor_path
        except Exception as error:
            logger.error("Failed to save preprocessor", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def initiate_data_transformation(self) -> DataTransformationArtifact:
        try:
            logger.info("Data transformation started")

            train_data_path, test_data_path = self._get_train_test_paths()
            schema = read_yaml_file(self.data_transformation_config.schema_path)

            train_dataframe = self.read_dataframe(train_data_path)
            test_dataframe = self.read_dataframe(test_data_path)

            if train_dataframe.empty or test_dataframe.empty:
                raise ValueError("Train or test dataframe is empty")

            train_features, train_target = self.separate_features_and_target(
                train_dataframe,
                schema,
            )
            test_features, test_target = self.separate_features_and_target(
                test_dataframe,
                schema,
            )

            (
                transformed_train_features,
                transformed_test_features,
                preprocessor,
            ) = self.transform_train_test_data(train_features, test_features)

            resampled_train_features, resampled_train_target = self.apply_smote_resampling(
                transformed_train_features,
                train_target,
            )

            feature_columns = list(schema["columns"].keys())
            target_column = schema["target_column"]

            transformed_train_dataframe = self._build_transformed_dataframe(
                resampled_train_features,
                resampled_train_target,
                feature_columns,
                target_column,
            )
            transformed_test_dataframe = self._build_transformed_dataframe(
                transformed_test_features,
                test_target.to_numpy(),
                feature_columns,
                target_column,
            )

            transformed_train_path, transformed_test_path = self.save_transformed_data(
                transformed_train_dataframe,
                transformed_test_dataframe,
            )
            preprocessor_path = self.save_preprocessor(preprocessor)

            data_transformation_artifact = DataTransformationArtifact(
                transformed_train_path=transformed_train_path,
                transformed_test_path=transformed_test_path,
                preprocessor_path=preprocessor_path,
                train_data_path=train_data_path,
                test_data_path=test_data_path,
            )

            logger.info("Data transformation completed: %s", data_transformation_artifact)
            return data_transformation_artifact
        except Exception as error:
            logger.error("Data transformation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)
