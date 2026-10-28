import logging
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from resume_agent.loaders.loader import ResumeLoader


LOGGER = logging.getLogger(__name__)


class ResumeStore:

    def __init__(
        self,
        loader: ResumeLoader,
        persist_directory: str = "data/chroma_db",
    ):
        self.loader = loader
        self.persist_directory = persist_directory
        self.collection_name = "resumes"

        # Original model load kept for reference and disabled to avoid repeated startup downloads.
        # self._embedding_model = HuggingFaceEmbeddings(
        #     model_name="sentence-transformers/all-MiniLM-L6-v2"
        # )
        try:
            from main import get_shared_embedding_model
            self._embedding_model = get_shared_embedding_model()
        except Exception:
            self._embedding_model = None

        self._store = None

    @property
    def records(self) -> dict[str, dict[str, Any]]:
        return self.loader.records()

    def _store_documents(
        self,
        documents: list[Document],
    ) -> None:

        if self._store is None:
            self._store = Chroma.from_documents(
                documents=documents,
                embedding=self._embedding_model,
                collection_name=self.collection_name,
                persist_directory=str(
                    self.persist_directory
                ),
            )

            LOGGER.info(
                f"Created new Chroma collection "
                f"'{self.collection_name}' and stored "
                f"{len(documents)} documents."
            )

        else:
            self._store.add_documents(documents)

            LOGGER.info(
                f"Added {len(documents)} documents to "
                f"existing Chroma collection "
                f"'{self.collection_name}'."
            )

    def _search(
        self,
        query: str,
        *,
        filename: str | None = None,
        k: int = 8,
    ) -> list[dict[str, Any]]:

        self._require_resumes()

        default_filename = self._default_filename()

        selected_filename = filename or default_filename

        filter_data = (
            {"filename": selected_filename}
            if selected_filename
            else None
        )

        LOGGER.info(
            f"Searching for query: '{query}' "
            f"with filename: {selected_filename}"
        )

        if filter_data:
            documents = self._store.similarity_search(
                query,
                k=k,
                filter=filter_data,
            )
        else:
            documents = self._store.similarity_search(
                query,
                k=k,
            )

        return [
            {
                "filename": item.metadata["filename"],
                "candidate_name": item.metadata["candidate_name"],
                "content": item.page_content,
            }
            for item in documents
        ]

    def _require_resumes(self) -> None:

        if not self.records or self._store is None:
            LOGGER.error(
                "No resumes loaded. Please load at least "
                "one resume before performing this operation."
            )

            raise RuntimeError(
                "Load at least one resume before using "
                "this operation."
            )

    def _default_filename(self) -> str | None:

        if len(self.records) == 1:
            return next(
                iter(self.records.values())
            )["filename"]

        return None