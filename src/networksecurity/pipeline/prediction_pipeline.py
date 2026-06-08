class PredictionPipeline:
    def predict(self, payload: dict) -> dict:
        """Return placeholder prediction until model loading is implemented."""
        return {"prediction": None, "input": payload}
