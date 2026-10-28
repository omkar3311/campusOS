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

            # Original model load kept for reference and disabled to avoid repeated startup downloads.
            # self.model = HuggingFaceEmbeddings(
            #     model_name=(
            #         settings.embedding_model_name
            #     ),
            #     model_kwargs={
            #         "device": settings.embedding_device
            #     },
            #     encode_kwargs={
            #         "normalize_embeddings": (
            #             settings.normalize_embeddings
            #         )
            #     }
            # )
            try:
                from main import get_shared_embedding_model
                self.model = get_shared_embedding_model()
            except Exception:
                self.model = None

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