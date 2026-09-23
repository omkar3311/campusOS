from study_agent.logger import LOGGER


class Retriever:

    def __init__(
        self,
        vectorstore,
        k: int
    ):

        self.vectorstore = vectorstore
        self.k = k

        LOGGER.debug(
            "Retriever initialized. k=%d",
            self.k
        )

    def retrieve(
        self,
        query: str
    ):

        if not query:

            LOGGER.warning(
                "Empty query received."
            )

            return []

        LOGGER.info(
            "Retrieving relevant documents."
        )

        try:

            results = (
                self.vectorstore
                .similarity_search_with_score(
                    query,
                    k=self.k
                )
            )

            LOGGER.info(
                "Retrieved %d documents.",
                len(results)
            )

            return results

        except Exception:

            LOGGER.exception(
                "Document retrieval failed."
            )

            raise