# Network Security ML/MLOps Project

End-to-end network security project with ETL, MongoDB integration, machine learning, API serving, and MLOps structure.

## Project Structure

```text
.
├── .github/workflows/main.yaml
├── app.py
├── main.py
├── setup.py
├── requirements.txt
├── dockerfile
├── config/
├── data/
├── notebooks/
├── artifacts/
├── logs/
├── saved_models/
├── prediction_output/
├── src/networksecurity/
└── tests/
```

## Setup

```bash
conda activate "/Users/sankalpmakol/Desktop/Network Security/venv"
python -m pip install -r requirements.txt
```

## Run Training Pipeline

```bash
python main.py
```

## Run API

```bash
uvicorn app:app --reload
```
