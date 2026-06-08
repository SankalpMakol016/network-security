from fastapi import FastAPI

from networksecurity.pipeline.prediction_pipeline import PredictionPipeline


app = FastAPI(title="Network Security Prediction API")


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "Network Security API is running"}


@app.post("/predict")
def predict(payload: dict) -> dict:
    pipeline = PredictionPipeline()
    return pipeline.predict(payload)
