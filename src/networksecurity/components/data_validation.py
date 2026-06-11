import json
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

from networksecurity.constants import CONFIG_FILE_PATH, SCHEMA_FILE_PATH
from networksecurity.entity.artifact_entity import (
    DataIngestionArtifact,
    DataValidationArtifact,
)
from networksecurity.entity.config_entity import DataValidationConfig
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.utils.main_utils import read_yaml_file


class DataValidation:
    def __init__(
        self,
        data_ingestion_artifact: DataIngestionArtifact | None = None,
        data_validation_config: DataValidationConfig | None = None,
    ) -> None:
        try:
            self.data_ingestion_artifact = data_ingestion_artifact
            self.data_validation_config = (
                data_validation_config or self.get_data_validation_config()
            )
        except Exception as error:
            logger.error("Failed to initialize DataValidation", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def get_data_validation_config() -> DataValidationConfig:
        try:
            config = read_yaml_file(CONFIG_FILE_PATH)
            validation_config = config["data_validation"]

            return DataValidationConfig(
                train_data_path=config["paths"]["train_data"],
                test_data_path=config["paths"]["test_data"],
                schema_path=SCHEMA_FILE_PATH,
                validation_report_path=validation_config["validation_report_path"],
                drift_p_value_threshold=validation_config["drift_p_value_threshold"],
                missing_value_threshold=validation_config["missing_value_threshold"],
            )
        except Exception as error:
            logger.error("Failed to read data validation configuration", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def _get_train_test_paths(self) -> tuple[str, str]:
        if self.data_ingestion_artifact is not None:
            return (
                self.data_ingestion_artifact.train_data_path,
                self.data_ingestion_artifact.test_data_path,
            )

        return (
            self.data_validation_config.train_data_path,
            self.data_validation_config.test_data_path,
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

    def validate_columns(
        self,
        dataframe: pd.DataFrame,
        schema: dict,
    ) -> dict[str, bool | list[str]]:
        try:
            expected_columns = set(schema["columns"].keys())
            expected_columns.add(schema["target_column"])
            actual_columns = set(dataframe.columns)

            missing_columns = sorted(expected_columns - actual_columns)
            extra_columns = sorted(actual_columns - expected_columns)

            is_valid = not missing_columns

            validation_result = {
                "is_valid": is_valid,
                "expected_column_count": len(expected_columns),
                "actual_column_count": len(actual_columns),
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
            }

            logger.info("Column validation result: %s", validation_result)
            return validation_result
        except Exception as error:
            logger.error("Column validation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def validate_dtypes(
        self,
        dataframe: pd.DataFrame,
        schema: dict,
    ) -> dict[str, bool | dict[str, str]]:
        try:
            dtype_mismatches: dict[str, str] = {}

            for column_name, column_schema in schema["columns"].items():
                if column_name not in dataframe.columns:
                    continue

                expected_dtype = column_schema["dtype"]
                series = dataframe[column_name]

                if expected_dtype == "int":
                    numeric_series = pd.to_numeric(series, errors="coerce")
                    if numeric_series.isna().any() and series.notna().any():
                        dtype_mismatches[column_name] = (
                            f"expected int-compatible values, found non-numeric values"
                        )
                    elif not pd.api.types.is_integer_dtype(numeric_series.dropna()):
                        dtype_mismatches[column_name] = (
                            f"expected int, found {series.dtype}"
                        )
                elif expected_dtype == "float":
                    if not pd.api.types.is_numeric_dtype(series):
                        dtype_mismatches[column_name] = (
                            f"expected float, found {series.dtype}"
                        )
                elif expected_dtype == "str":
                    if not pd.api.types.is_string_dtype(series.astype(str)):
                        dtype_mismatches[column_name] = (
                            f"expected str, found {series.dtype}"
                        )

            target_column = schema["target_column"]
            if target_column in dataframe.columns:
                target_series = dataframe[target_column]
                numeric_target = pd.to_numeric(target_series, errors="coerce")
                if numeric_target.isna().any() and target_series.notna().any():
                    dtype_mismatches[target_column] = (
                        "expected int-compatible target values, found non-numeric values"
                    )

            validation_result = {
                "is_valid": not dtype_mismatches,
                "dtype_mismatches": dtype_mismatches,
            }

            logger.info("Datatype validation result: %s", validation_result)
            return validation_result
        except Exception as error:
            logger.error("Datatype validation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def validate_missing_values(
        self,
        dataframe: pd.DataFrame,
        schema: dict,
    ) -> dict[str, bool | dict[str, float]]:
        try:
            threshold = self.data_validation_config.missing_value_threshold
            columns_to_check = list(schema["columns"].keys()) + [schema["target_column"]]

            missing_ratios: dict[str, float] = {}
            for column_name in columns_to_check:
                if column_name not in dataframe.columns:
                    continue

                missing_ratio = float(dataframe[column_name].isna().mean())
                if missing_ratio > threshold:
                    missing_ratios[column_name] = missing_ratio

            validation_result = {
                "is_valid": not missing_ratios,
                "threshold": threshold,
                "columns_exceeding_threshold": missing_ratios,
            }

            logger.info("Missing value validation result: %s", validation_result)
            return validation_result
        except Exception as error:
            logger.error("Missing value validation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def detect_drift(
        self,
        train_dataframe: pd.DataFrame,
        test_dataframe: pd.DataFrame,
        schema: dict,
    ) -> dict[str, bool | dict[str, dict[str, float | bool]]]:
        try:
            threshold = self.data_validation_config.drift_p_value_threshold
            drift_details: dict[str, dict[str, float | bool]] = {}

            for column_name in schema["columns"].keys():
                if column_name not in train_dataframe.columns:
                    continue
                if column_name not in test_dataframe.columns:
                    continue

                train_series = pd.to_numeric(
                    train_dataframe[column_name],
                    errors="coerce",
                ).dropna()
                test_series = pd.to_numeric(
                    test_dataframe[column_name],
                    errors="coerce",
                ).dropna()

                if train_series.empty or test_series.empty:
                    continue

                statistic, p_value = stats.ks_2samp(train_series, test_series)
                drift_details[column_name] = {
                    "drift_detected": bool(p_value < threshold),
                    "p_value": float(p_value),
                    "statistic": float(statistic),
                }

            drift_detected = any(
                column_report["drift_detected"] for column_report in drift_details.values()
            )

            validation_result = {
                "is_valid": bool(not drift_detected),
                "threshold": threshold,
                "drift_details": drift_details,
            }

            logger.info("Drift detection result: drift_detected=%s", drift_detected)
            return validation_result
        except Exception as error:
            logger.error("Drift detection failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def save_validation_report(self, report: dict) -> str:
        try:
            report_path = Path(self.data_validation_config.validation_report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with report_path.open("w", encoding="utf-8") as report_file:
                json.dump(report, report_file, indent=4)

            logger.info("Saved validation report to %s", report_path)
            return str(report_path)
        except Exception as error:
            logger.error("Failed to save validation report", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def initiate_data_validation(self) -> DataValidationArtifact:
        try:
            logger.info("Data validation started")

            train_data_path, test_data_path = self._get_train_test_paths()
            schema = read_yaml_file(self.data_validation_config.schema_path)

            train_dataframe = self.read_dataframe(train_data_path)
            test_dataframe = self.read_dataframe(test_data_path)

            if train_dataframe.empty or test_dataframe.empty:
                raise ValueError("Train or test dataframe is empty")

            column_validation = {
                "train": self.validate_columns(train_dataframe, schema),
                "test": self.validate_columns(test_dataframe, schema),
            }
            dtype_validation = {
                "train": self.validate_dtypes(train_dataframe, schema),
                "test": self.validate_dtypes(test_dataframe, schema),
            }
            missing_value_validation = {
                "train": self.validate_missing_values(train_dataframe, schema),
                "test": self.validate_missing_values(test_dataframe, schema),
            }
            drift_validation = self.detect_drift(train_dataframe, test_dataframe, schema)

            is_valid = all(
                [
                    column_validation["train"]["is_valid"],
                    column_validation["test"]["is_valid"],
                    dtype_validation["train"]["is_valid"],
                    dtype_validation["test"]["is_valid"],
                    missing_value_validation["train"]["is_valid"],
                    missing_value_validation["test"]["is_valid"],
                    drift_validation["is_valid"],
                ]
            )

            validation_report = {
                "is_valid": bool(is_valid),
                "train_data_path": train_data_path,
                "test_data_path": test_data_path,
                "column_validation": column_validation,
                "dtype_validation": dtype_validation,
                "missing_value_validation": missing_value_validation,
                "drift_validation": drift_validation,
            }

            validation_report_path = self.save_validation_report(validation_report)

            if not is_valid:
                raise ValueError(
                    f"Data validation failed. See report at {validation_report_path}"
                )

            data_validation_artifact = DataValidationArtifact(
                validation_report_path=validation_report_path,
                is_valid=is_valid,
                train_data_path=train_data_path,
                test_data_path=test_data_path,
            )

            logger.info("Data validation completed: %s", data_validation_artifact)
            return data_validation_artifact
        except Exception as error:
            logger.error("Data validation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)
