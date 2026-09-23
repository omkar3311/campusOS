from pathlib import Path
from typing import List, Optional
import shutil

from langchain_chroma import Chroma
from langchain_core.documents import Document

from study_agent.logger import LOGGER


class ChromaStore:

    def __init__(
        self,
        persist_directory: Path,
        embedding_model
    ):
        self.persist_directory = Path(persist_directory)
        self.embedding_model = embedding_model
        self.collection_name = "study_agent_collection"
        self._database: Optional[Chroma] = None

        LOGGER.debug(
            "ChromaStore initialized. Directory: %s",
            self.persist_directory
        )

    def exists(self) -> bool:
        if self._database is not None:
            return True
        if not self.persist_directory.exists():
            return False
        return any(self.persist_directory.iterdir())

    def create(self, documents: list[Document]):
        if not documents:
            LOGGER.warning("Cannot create Chroma database with no documents.")
            raise ValueError("Documents cannot be empty.")

        LOGGER.info("Creating Chroma vector database with %d documents.", len(documents))
        try:
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self._database = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                collection_name=self.collection_name,
                persist_directory=str(self.persist_directory)
            )
            LOGGER.info("Chroma database created successfully on disk.")
            return self._database
        except Exception:
            LOGGER.exception("Failed to create Chroma on disk, creating in-memory Chroma instance.")
            self._database = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                collection_name=self.collection_name
            )
            return self._database

    def load(self):
        if self._database is not None:
            return self._database

        if not self.exists():
            LOGGER.error("Chroma database does not exist.")
            raise FileNotFoundError("Chroma database does not exist.")

        try:
            self._database = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embedding_model,
                collection_name=self.collection_name
            )
            LOGGER.info("Chroma database loaded successfully from disk.")
            return self._database
        except Exception:
            LOGGER.exception("Failed to load Chroma from disk, initializing in-memory store.")
            self._database = Chroma(
                embedding_function=self.embedding_model,
                collection_name=self.collection_name
            )
            return self._database

    def add_documents(self, documents: list[Document]):
        if self._database is None:
            return self.create(documents)
        try:
            self._database.add_documents(documents)
            LOGGER.info("Added %d documents to Chroma.", len(documents))
            return self._database
        except Exception:
            LOGGER.exception("Failed to add to persistent collection, re-creating in-memory store.")
            return self.create(documents)

    def reset(self):
        LOGGER.info("Resetting Chroma vector store.")
        self._database = None
        if self.persist_directory.exists():
            try:
                shutil.rmtree(self.persist_directory, ignore_errors=True)
                self.persist_directory.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass