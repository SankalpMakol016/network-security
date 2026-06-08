from pathlib import Path

import joblib


def save_object(file_path: str, obj: object) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, path)


def load_object(file_path: str) -> object:
    return joblib.load(file_path)
