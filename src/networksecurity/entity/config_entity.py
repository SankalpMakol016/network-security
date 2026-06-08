from dataclasses import dataclass


@dataclass
class DataIngestionConfig:
    database_name: str
    collection_name: str
    raw_data_path: str
