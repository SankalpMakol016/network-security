from dataclasses import dataclass


@dataclass
class DataIngestionConfig:
    database_name: str
    collection_name: str
    raw_data_path: str
    train_data_path: str
    test_data_path: str
    test_size: float


@dataclass
class DataValidationConfig:
    train_data_path: str
    test_data_path: str
    schema_path: str
    validation_report_path: str
    drift_p_value_threshold: float
    missing_value_threshold: float


@dataclass
class DataTransformationConfig:
    train_data_path: str
    test_data_path: str
    schema_path: str
    transformed_train_path: str
    transformed_test_path: str
    preprocessor_path: str
    apply_smote: bool
    smote_random_state: int
