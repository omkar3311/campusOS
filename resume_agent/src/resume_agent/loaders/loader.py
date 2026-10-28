import logging
import re
import uuid
from pathlib import Path
from typing import Any, Sequence

from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from resume_agent.memory.memory import Profile


LOGGER = logging.getLogger(__name__)


class ResumeLoader:

    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 150

        # Original model load kept for reference and disabled to avoid repeated startup downloads.
        # self.embeddings = HuggingFaceEmbeddings(
        #     model_name="sentence-transformers/all-MiniLM-L6-v2"
        # )
        try:
            from main import get_shared_embedding_model
            self.embeddings = get_shared_embedding_model()
        except Exception:
            self.embeddings = None

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )

        self.profile_memory = Profile()
        self._records: dict[str, dict[str, Any]] = {}

    def load_resume(
        self,
        paths: str | Path | Sequence[str | Path],
    ) -> list[str]:

        path_list = (
            [paths]
            if isinstance(paths, (str, Path))
            else list(paths)
        )

        if not path_list:
            LOGGER.error("No resume paths provided.")
            raise ValueError(
                "Provide at least one PDF or DOCX resume."
            )

        documents: list[Document] = []
        loaded: list[str] = []

        for raw_path in path_list:
            path = Path(raw_path).expanduser().resolve()

            if not path.is_file():
                raise FileNotFoundError(
                    f"Resume not found: {path}"
                )

            loader = self._loader_for(path)

            LOGGER.info(
                f"Loading resume from {path.name}"
            )

            pages = loader.load()

            text = "\n".join(
                page.page_content
                for page in pages
            ).strip()

            if not text:
                raise ValueError(
                    f"No readable text was found in {path.name}."
                )

            resume_id = uuid.uuid4().hex

            candidate_name = self._candidate_name(
                text,
                path.stem,
            )

            if (
                self.profile_memory.get_profile(
                    candidate_name
                )
                is None
            ):
                self.profile_memory.make_profile(
                    candidate_name,
                    text,
                )

                LOGGER.info(
                    f"Profile created for {candidate_name}"
                )

            chunks = self.text_splitter.split_documents(
                pages
            )

            LOGGER.info(
                f"Split {path.name} into "
                f"{len(chunks)} chunks."
            )

            for index, chunk in enumerate(chunks):
                chunk.metadata.update(
                    {
                        "filename": path.name,
                        "candidate_name": candidate_name,
                        "resume_id": resume_id,
                        "chunk_index": index,
                    }
                )

            documents.extend(chunks)

            self._records[resume_id] = {
                "filename": path.name,
                "candidate_name": candidate_name,
                "text": text,
            }

            loaded.append(path.name)

            LOGGER.info(
                f"Loaded resume: {path.name} "
                f"with ID: {resume_id}"
            )

        LOGGER.info(
            f"Loaded {len(loaded)} resume(s) with "
            f"{len(documents)} chunk(s)."
        )

        return loaded , documents

    @staticmethod
    def _loader_for(path: Path) -> Any:

        if path.suffix.lower() == ".pdf":
            return PyMuPDFLoader(str(path))

        if path.suffix.lower() == ".docx":
            return Docx2txtLoader(str(path))

        raise ValueError(
            "Only PDF and DOCX files are supported."
        )

    @staticmethod
    def _candidate_name(
        text: str,
        fallback: str,
    ) -> str:

        for line in text.splitlines()[:8]:
            candidate = re.sub(
                r"\s+",
                " ",
                line,
            ).strip()

            if (
                2 <= len(candidate.split()) <= 5
                and "@" not in candidate
                and not re.search(
                    r"\d{5,}",
                    candidate,
                )
            ):
                return candidate.title()

        return fallback

    def records(self) -> dict[str, dict[str, Any]]:
        return self._records

    def _resume_catalog(self) -> str:

        lines = ["Loaded resumes:\n"]

        for record in self._records.values():
            lines.append(
                f"- Filename: {record['filename']}\n"
                f"  Candidate: {record['candidate_name']}"
            )

        lines.append(
            "\nIMPORTANT:\n"
            "- Use only these filenames.\n"
            "- Never invent filenames.\n"
            "- If one resume is loaded, use that resume by default."
        )

        return "\n".join(lines)