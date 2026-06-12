import sys
from pathlib import Path

import pandas as pd

from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logger
from networksecurity.utils.ml_utils import load_object


SAVED_MODEL_PATH = Path("artifacts/saved_model/model.pkl")
PREPROCESSOR_PATH = Path("artifacts/preprocessor/preprocessor.pkl")


class PredictionPipeline:
    """
    Loads the trained model and preprocessor and performs inference.
    """

    def __init__(
        self,
        model_path: Path = SAVED_MODEL_PATH,
        preprocessor_path: Path = PREPROCESSOR_PATH,
    ) -> None:
        try:
            logger.info("Loading prediction artifacts")

            self.model = load_object(model_path)
            self.preprocessor = load_object(preprocessor_path)

            logger.info("Prediction artifacts loaded successfully")

        except Exception as error:
            logger.error(
                "Failed to initialize PredictionPipeline",
                exc_info=True,
            )
            raise NetworkSecurityException(error, sys)

    def predict(self, dataframe: pd.DataFrame):
        try:
            logger.info(
                "Received dataframe for prediction with shape %s",
                dataframe.shape,
            )

            transformed_features = self.preprocessor.transform(
                dataframe
            )

            predictions = self.model.predict(
                transformed_features
            )

            logger.info(
                "Prediction completed for %s records",
                len(predictions),
            )

            return predictions

        except Exception as error:
            logger.error(
                "Prediction failed",
                exc_info=True,
            )
            raise NetworkSecurityException(error, sys)