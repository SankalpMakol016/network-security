from networksecurity.pipeline.training_pipeline import TrainingPipeline


def test_training_pipeline_can_be_created() -> None:
    assert TrainingPipeline() is not None
 