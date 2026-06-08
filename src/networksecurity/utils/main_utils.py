from pathlib import Path

import yaml


def read_yaml_file(file_path: str) -> dict:
    with Path(file_path).open("r", encoding="utf-8") as yaml_file:
        return yaml.safe_load(yaml_file)
