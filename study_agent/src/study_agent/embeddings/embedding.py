from langchain_huggingface import (
    HuggingFaceEmbeddings
)

from study_agent.config import settings
from study_agent.logger import LOGGER


class EmbeddingModel:

    def __init__(self):

        LOGGER.info(
            "Loading embedding model: %s",
            settings.embedding_model_name
        )

        try:

            self.model = HuggingFaceEmbeddings(
                model_name=(
                    settings.embedding_model_name
                ),
                model_kwargs={
                    "device": settings.embedding_device
                },
                encode_kwargs={
                    "normalize_embeddings": (
                        settings.normalize_embeddings
                    )
                }
            )

            LOGGER.info(
                "Embedding model loaded successfully."
            )

        except Exception:

            LOGGER.exception(
                "Failed to load embedding model."
            )

            raise

    def get_model(self):

        return self.model