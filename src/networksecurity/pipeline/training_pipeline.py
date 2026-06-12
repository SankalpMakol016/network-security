from networksecurity.components.data_ingestion import DataIngestion
from networksecurity.components.data_transformation import DataTransformation
from networksecurity.components.data_validation import DataValidation
from networksecurity.components.model_evaluation import ModelEvaluation
from networksecurity.components.model_trainer import ModelTrainer


class TrainingPipeline:
    def run(self) -> None:
        data_ingestion_artifact = DataIngestion().initiate_data_ingestion()
        data_validation_artifact = DataValidation(
            data_ingestion_artifact=data_ingestion_artifact,
        ).initiate_data_validation()
        data_transformation_artifact = DataTransformation(
            data_validation_artifact=data_validation_artifact,
        ).initiate_data_transformation()
        model_trainer_artifact = ModelTrainer(
            data_transformation_artifact=data_transformation_artifact,
        ).initiate_model_training()
        model_evaluation_artifact=ModelEvaluation(
            model_trainer_artifact=model_trainer_artifact,
        ).initiate_model_evaluation()
        