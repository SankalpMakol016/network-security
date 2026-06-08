from networksecurity.components.data_ingestion import DataIngestion
from networksecurity.components.data_transformation import DataTransformation
from networksecurity.components.data_validation import DataValidation
from networksecurity.components.model_evaluation import ModelEvaluation
from networksecurity.components.model_pusher import ModelPusher
from networksecurity.components.model_trainer import ModelTrainer


class TrainingPipeline:
    def run(self) -> None:
        DataIngestion().initiate_data_ingestion()
        DataValidation().initiate_data_validation()
        DataTransformation().initiate_data_transformation()
        ModelTrainer().initiate_model_training()
        ModelEvaluation().initiate_model_evaluation()
        ModelPusher().initiate_model_pusher()
