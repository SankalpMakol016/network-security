from dataclasses import dataclass


@dataclass
class DataIngestionArtifact:
    raw_data_path: str
    train_data_path: str
    test_data_path: str


@dataclass
class DataValidationArtifact:
    validation_report_path: str
    is_valid: bool
    train_data_path: str
    test_data_path: str


@dataclass
class DataTransformationArtifact:
    transformed_train_path: str
    transformed_test_path: str
    preprocessor_path: str
    train_data_path: str
    test_data_path: str


@dataclass
class ModelTrainerArtifact:
    trained_model_path: str
    transformed_train_path: str
    transformed_test_path: str


@dataclass
class ModelEvaluationArtifact:
    evaluation_report_path: str
    trained_model_path: str
    is_acceptable: bool

