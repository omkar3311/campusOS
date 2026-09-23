from sentence_transformers import (
    CrossEncoder
)

from study_agent.config import settings
from study_agent.logger import LOGGER


class DocumentReranker:

    def __init__(self):

        LOGGER.info(
            "Loading reranker model: %s",
            settings.reranker_model_name
        )

        try:

            self.model = CrossEncoder(
                settings.reranker_model_name
            )

            LOGGER.info(
                "Reranker model loaded successfully."
            )

        except Exception:

            LOGGER.exception(
                "Failed to load reranker model."
            )

            raise

    def rerank(
        self,
        query: str,
        documents,
        top_k: int
    ):

        if not documents:

            LOGGER.warning(
                "No documents available for reranking."
            )

            return []

        LOGGER.info(
            "Reranking %d documents.",
            len(documents)
        )

        document_list = [
            document
            for document, _score
            in documents
        ]

        pairs = [
            (
                query,
                document.page_content
            )
            for document
            in document_list
        ]

        try:

            scores = self.model.predict(
                pairs
            )

            ranked_documents = sorted(
                zip(
                    scores,
                    document_list
                ),
                key=lambda item: item[0],
                reverse=True
            )

            final_documents = []

            for rank, (
                score,
                document
            ) in enumerate(
                ranked_documents[:top_k],
                start=1
            ):

                LOGGER.debug(
                    "Rank %d | Score: %.4f",
                    rank,
                    float(score)
                )

                final_documents.append(
                    document
                )

            LOGGER.info(
                "Selected top %d documents.",
                len(final_documents)
            )

            return final_documents

        except Exception:

            LOGGER.exception(
                "Document reranking failed."
            )

            raise