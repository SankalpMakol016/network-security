from dataclasses import dataclass


@dataclass
class DataIngestionArtifact:
    raw_data_path: str
    train_data_path: str
    test_data_path: str
