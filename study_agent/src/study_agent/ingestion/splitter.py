from langchain_core.documents import Document

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from study_agent.config import settings
from study_agent.logger import LOGGER


class DocumentSplitter:

    def __init__(self):

        LOGGER.info(
            "Initializing document splitter."
        )

        self.splitter = (
            RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    " ",
                    ""
                ]
            )
        )

        LOGGER.info(
            "Document splitter initialized."
        )

    def split(
        self,
        documents: list[Document]
    ) -> list[Document]:

        if not documents:

            LOGGER.warning(
                "No documents received for splitting."
            )

            return []

        LOGGER.info(
            "Splitting %d documents.",
            len(documents)
        )

        try:

            chunks = (
                self.splitter.split_documents(
                    documents
                )
            )

            LOGGER.info(
                "Created %d chunks.",
                len(chunks)
            )

            return chunks

        except Exception:

            LOGGER.exception(
                "Document splitting failed."
            )

            raise