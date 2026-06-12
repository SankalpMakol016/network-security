import json
import sys
from pathlib import Path
import mlflow
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from networksecurity.constants import CONFIG_FILE_PATH, SCHEMA_FILE_PATH
from networksecurity.entity.artifact_entity import (
    ModelEvaluationArtifact,
    ModelTrainerArtifact,
)
from networksecurity.entity.config_entity import ModelEvaluationConfig
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.utils.main_utils import read_yaml_file
from networksecurity.utils.ml_utils import load_object


class ModelEvaluation:
    def __init__(
        self,
        model_trainer_artifact: ModelTrainerArtifact | None = None,
        model_evaluation_config: ModelEvaluationConfig | None = None,
    ) -> None:
        try:
            self.model_trainer_artifact = model_trainer_artifact
            self.model_evaluation_config = (
                model_evaluation_config or self.get_model_evaluation_config()
            )
        except Exception as error:
            logger.error("Failed to initialize ModelEvaluation", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def get_model_evaluation_config() -> ModelEvaluationConfig:
        try:
            config = read_yaml_file(CONFIG_FILE_PATH)
            evaluation_config = config["model_evaluation"]
            transformation_config = config["data_transformation"]
            training_config = config["model_training"]

            return ModelEvaluationConfig(
                transformed_train_path=transformation_config["transformed_train_path"],
                transformed_test_path=transformation_config["transformed_test_path"],
                schema_path=SCHEMA_FILE_PATH,
                trained_model_path=training_config["trained_model_path"],
                evaluation_report_path=evaluation_config["evaluation_report_path"],
                min_accuracy_threshold=evaluation_config["min_accuracy_threshold"],
                min_f1_threshold=evaluation_config["min_f1_threshold"],
            )
        except Exception as error:
            logger.error("Failed to read model evaluation configuration", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def _get_evaluation_paths(self) -> tuple[str, str, str]:
        if self.model_trainer_artifact is not None:
            return (
                self.model_trainer_artifact.transformed_train_path,
                self.model_trainer_artifact.transformed_test_path,
                self.model_trainer_artifact.trained_model_path,
            )

        return (
            self.model_evaluation_config.transformed_train_path,
            self.model_evaluation_config.transformed_test_path,
            self.model_evaluation_config.trained_model_path,
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

            return features, target
        except Exception as error:
            logger.error("Failed to separate features and target", exc_info=True)
            raise NetworkSecurityException(error, sys)

    @staticmethod
    def calculate_metrics(
        target: pd.Series,
        predictions: pd.Series | list[int],
        probabilities: list[float] | None = None,
    ) -> dict[str, float]:
        try:
            metrics = {
                "accuracy": float(accuracy_score(target, predictions)),
                "precision": float(precision_score(target, predictions, zero_division=0)),
                "recall": float(recall_score(target, predictions, zero_division=0)),
                "f1_score": float(f1_score(target, predictions, zero_division=0)),
            }

            if probabilities is not None:
                metrics["roc_auc"] = float(roc_auc_score(target, probabilities))

            return metrics
        except Exception as error:
            logger.error("Failed to calculate evaluation metrics", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def evaluate_model(
        self,
        model: object,
        test_features: pd.DataFrame,
        test_target: pd.Series,
    ) -> dict[str, float]:
        try:
            predictions = model.predict(test_features)
            probabilities = None

            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba(test_features)[:, 1]

            metrics = self.calculate_metrics(test_target, predictions, probabilities)
            logger.info("Model evaluation metrics: %s", metrics)
            return metrics
        except Exception as error:
            logger.error("Model evaluation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def evaluate_baseline_model(
        self,
        train_features: pd.DataFrame,
        train_target: pd.Series,
        test_features: pd.DataFrame,
        test_target: pd.Series,
    ) -> dict[str, float]:
        try:
            baseline_model = DummyClassifier(strategy="most_frequent")
            baseline_model.fit(train_features, train_target)

            predictions = baseline_model.predict(test_features)
            metrics = self.calculate_metrics(test_target, predictions)
            logger.info("Baseline evaluation metrics: %s", metrics)
            return metrics
        except Exception as error:
            logger.error("Baseline model evaluation failed", exc_info=True)
            raise NetworkSecurityException(error, sys)

    def save_evaluation_report(self, report: dict) -> str:
        try:
            report_path = Path(self.model_evaluation_config.evaluation_report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with report_path.open("w", encoding="utf-8") as report_file:
                json.dump(report, report_file, indent=4)

            logger.info("Saved evaluation report to %s", report_path)
            return str(report_path)
        except Exception as error:
            logger.error("Failed to save evaluation report", exc_info=True)
            raise NetworkSecurityException(error, sys)
        
    def log_to_mlflow(self,model:object,train_metrics:dict,test_metrics:dict):
        with mlflow.start_run():
            # parameters
            mlflow.log_params(
                model.get_params()
            )
            # train metrics
            mlflow.log_metrics(
                {
                    "train_accuracy": train_metrics["accuracy"],
                    "train_precision": train_metrics["precision"],
                    "train_recall": train_metrics["recall"],
                    "train_f1": train_metrics["f1_score"],
                    "train_roc_auc" : train_metrics["roc_auc"],
                }
            )
            # test metrics
            mlflow.log_metrics(
                {
                    "test_accuracy": test_metrics["accuracy"],
                    "test_precision": test_metrics["precision"],
                    "test_recall": test_metrics["recall"],
                    "test_f1": test_metrics["f1_score"],
                    "test_roc_auc" : test_metrics["roc_auc"],
                }
            )
            # model artifact
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model"
            )
        

    def initiate_model_evaluation(self) -> ModelEvaluationArtifact:
        try:
            logger.info("Model evaluation started")

            (
                transformed_train_path,
                transformed_test_path,
                trained_model_path,
            ) = self._get_evaluation_paths()
            schema = read_yaml_file(self.model_evaluation_config.schema_path)

            train_dataframe = self.read_dataframe(transformed_train_path)
            test_dataframe = self.read_dataframe(transformed_test_path)

            if train_dataframe.empty or test_dataframe.empty:
                raise ValueError("Transformed train or test dataframe is empty")

            train_features, train_target = self.separate_features_and_target(
                train_dataframe,
                schema,
            )
            test_features, test_target = self.separate_features_and_target(
                test_dataframe,
                schema,
            )

            model = load_object(trained_model_path)
            model_test_metrics = self.evaluate_model(model, test_features, test_target)
            model_train_metrics = self.evaluate_model(model,train_features,train_target)
            baseline_metrics = self.evaluate_baseline_model(
                train_features,
                train_target,
                test_features,
                test_target,
            )
            self.log_to_mlflow(model,model_train_metrics,model_test_metrics)
            

            is_acceptable = (
                model_test_metrics["accuracy"]
                >= self.model_evaluation_config.min_accuracy_threshold
                and model_test_metrics["f1_score"]
                >= self.model_evaluation_config.min_f1_threshold
            )

            evaluation_report = {
                "is_acceptable": bool(is_acceptable),
                "trained_model_path": trained_model_path,
                "transformed_test_path": transformed_test_path,
                "thresholds": {
                    "min_accuracy": self.model_evaluation_config.min_accuracy_threshold,
                    "min_f1_score": self.model_evaluation_config.min_f1_threshold,
                },
                "model_metrics": model_test_metrics,
                "baseline_metrics": baseline_metrics,
                "improvement_over_baseline": {
                    metric_name: float(
                        model_test_metrics[metric_name] - baseline_metrics[metric_name]
                    )
                    for metric_name in model_test_metrics
                    if metric_name in baseline_metrics
                },
            }

            evaluation_report_path = self.save_evaluation_report(evaluation_report)

            if not is_acceptable:
                raise ValueError(
                    f"Model evaluation failed thresholds. See report at {evaluation_report_path}"
                )

            model_evaluation_artifact = ModelEvaluationArtifact(
                evaluation_report_path=evaluation_report_path,
                trained_model_path=trained_model_path,
                is_acceptable=is_acceptable,
            )

            logger.info("Model evaluation completed: %s", model_evaluation_artifact)
            return model_evaluation_artifact
        except Exception as error:
            logger.error("Model evaluation pipeline failed", exc_info=True)
            raise NetworkSecurityException(error, sys)
