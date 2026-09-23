from pathlib import Path

from langchain_community.document_loaders import (
    PyMuPDFLoader
)

from langchain_core.documents import Document

from study_agent.logger import LOGGER


class PDFLoader:

    def __init__(self):

        LOGGER.debug(
            "PDFLoader initialized."
        )

    def load(
        self,
        pdf_path: Path
    ) -> list[Document]:

        LOGGER.info(
            "Loading PDF: %s",
            pdf_path
        )

        if not pdf_path.exists():

            LOGGER.error(
                "PDF file does not exist: %s",
                pdf_path
            )

            raise FileNotFoundError(
                f"PDF file not found: {pdf_path}"
            )

        if pdf_path.suffix.lower() != ".pdf":

            LOGGER.error(
                "Unsupported file type: %s",
                pdf_path.suffix
            )

            raise ValueError(
                "Only PDF files are supported."
            )

        try:

            loader = PyMuPDFLoader(
                str(pdf_path)
            )

            documents = loader.load()

            LOGGER.info(
                "PDF loaded successfully. "
                "Pages: %d",
                len(documents)
            )

            return documents

        except Exception:

            LOGGER.exception(
                "PDF loading failed."
            )

            raise