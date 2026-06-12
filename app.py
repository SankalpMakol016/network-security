"""
app.py — FastAPI deployment layer for the Network Security MLOps project.

Run:
    uvicorn app:app --reload
"""

import io

import pandas as pd
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.pipeline.prediction_pipeline import PredictionPipeline


class PredictionResponse(BaseModel):
    status: str
    rows_processed: int
    predictions: list[int]


app = FastAPI(
    title="Network Security Prediction API",
    description=(
        "Upload a CSV file to the /predict endpoint and receive "
        "model predictions in JSON format."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def load_pipeline() -> None:
    try:
        logger.info("Loading PredictionPipeline...")
        app.state.pipeline = PredictionPipeline()
        logger.info("PredictionPipeline loaded successfully.")

    except Exception:
        logger.error(
            "Failed to load PredictionPipeline during startup.",
            exc_info=True,
        )
        app.state.pipeline = None


@app.get("/")
async def root():
    return {
        "service": "Network Security Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "predict": "/predict",
    }


@app.get("/health")
async def health_check():
    pipeline_ready = app.state.pipeline is not None

    return {
        "status": "ok" if pipeline_ready else "degraded",
        "pipeline_loaded": pipeline_ready,
    }


@app.post(
    "/predict",
    response_model=PredictionResponse,
)
async def predict(
    file: UploadFile = File(...)
) -> PredictionResponse:

    if app.state.pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction pipeline is unavailable.",
        )

    try:
        if (
            file.filename is None
            or not file.filename.lower().endswith(".csv")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload a CSV file.",
            )

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        dataframe = pd.read_csv(io.BytesIO(contents))

        # Remove target column if test.csv is uploaded
        if "Result" in dataframe.columns:
            dataframe = dataframe.drop(columns=["Result"])

        if dataframe.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV contains no rows.",
            )

        logger.info(
            "Received prediction request. DataFrame shape: %s",
            dataframe.shape,
        )

        predictions = app.state.pipeline.predict(dataframe)

        logger.info(
            "Successfully generated %s predictions.",
            len(predictions),
        )

        return PredictionResponse(
            status="success",
            rows_processed=len(dataframe),
            predictions=predictions.tolist(),
        )

    except HTTPException:
        raise

    except NetworkSecurityException as error:
        logger.error(
            "Prediction pipeline failed.",
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )

    except Exception as error:
        logger.error(
            "Unexpected prediction error.",
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
    )