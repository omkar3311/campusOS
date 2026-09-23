from pathlib import Path

from dotenv import load_dotenv

from study_agent.logger import LOGGER


class Settings:

    def __init__(self):

        load_dotenv()

        # =====================================
        # PROJECT
        # =====================================

        self.base_dir = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        # =====================================
        # DATA
        # =====================================

        self.data_dir = (
            self.base_dir / "data"
        )

        self.pdf_path = (
            self.data_dir / "rag.pdf"
        )

        # =====================================
        # VECTOR DATABASE
        # =====================================

        self.db_dir = (
            self.base_dir / "chroma_db"
        )

        # =====================================
        # EMBEDDING
        # =====================================

        self.embedding_model_name = (
            "sentence-transformers/"
            "all-MiniLM-L6-v2"
        )

        self.embedding_device = "cpu"

        self.normalize_embeddings = True

        # =====================================
        # RERANKER
        # =====================================

        self.reranker_model_name = (
            "cross-encoder/"
            "ms-marco-MiniLM-L-6-v2"
        )

        # =====================================
        # LLM
        # =====================================

        self.llm_model_name = (
            "qwen/qwen3.6-27b"
        )

        self.llm_temperature = 0

        # =====================================
        # CHUNKING
        # =====================================

        self.chunk_size = 1000

        self.chunk_overlap = 150

        # =====================================
        # RETRIEVAL
        # =====================================

        self.retrieval_k = 8

        self.rerank_top_k = 3

        # =====================================
        # GUARDRAILS
        # =====================================

        self.max_question_length = 3000

        self.max_context_length = 12000

        self.redact_pii = True

        LOGGER.info(
            "Application settings initialized."
        )


settings = Settings()