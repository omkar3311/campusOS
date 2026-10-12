from study_agent.config import settings

from study_agent.embeddings.embedding import (
    EmbeddingModel
)

from study_agent.guardrails import (
    GuardrailConfig,
    GuardrailViolation,
    Guardrails
)

from study_agent.ingestion.loader import (
    PDFLoader
)

from study_agent.ingestion.splitter import (
    DocumentSplitter
)

from study_agent.llm.chain import (
    LLMChain
)

from study_agent.llm.model import (
    LLMModel
)

from study_agent.logger import LOGGER

from study_agent.memory import (
    SessionMemory
)

from study_agent.retrieval.reranker import (
    DocumentReranker
)

from study_agent.retrieval.retriever import (
    Retriever
)

from study_agent.vectorstore.chroma import (
    ChromaStore
)


class RAGPipeline:

    def __init__(self):

        LOGGER.info(
            "Initializing RAG pipeline."
        )

        # =====================================
        # GUARDRAILS
        # =====================================

        guardrail_config = GuardrailConfig(
            max_question_length=(
                settings.max_question_length
            ),
            max_context_length=(
                settings.max_context_length
            ),
            redact_pii=(
                settings.redact_pii
            )
        )

        self.guardrails = Guardrails(
            guardrail_config
        )

        # =====================================
        # EMBEDDINGS
        # =====================================

        embedding = EmbeddingModel()

        self.embedding_model = (
            embedding.get_model()
        )

        # =====================================
        # VECTOR STORE
        # =====================================

        self.vectorstore = ChromaStore(
            persist_directory=settings.db_dir,
            embedding_model=self.embedding_model
        )

        # =====================================
        # RERANKER
        # =====================================

        self.reranker = (
            DocumentReranker()
        )

        # =====================================
        # LLM
        # =====================================

        self.llm_model = LLMModel()

        self.llm = LLMChain(
            guardrails=self.guardrails
        )

        # =====================================
        # SESSION MEMORY
        # =====================================

        self.session_memory = (
            SessionMemory(
                llm_model=self.llm_model
            )
        )

        LOGGER.info(
            "RAG pipeline initialized successfully."
        )

    def build_database(self):

        LOGGER.info(
            "Checking knowledge base."
        )

        if self.vectorstore.exists():

            LOGGER.info(
                "Knowledge base already exists."
            )

            return

        LOGGER.info(
            "Building knowledge base."
        )

        loader = PDFLoader()

        documents = loader.load(
            settings.pdf_path
        )

        if not documents:

            raise RuntimeError(
                "No documents were loaded."
            )

        splitter = DocumentSplitter()

        chunks = splitter.split(
            documents
        )

        if not chunks:

            raise RuntimeError(
                "No chunks were created."
            )

        self.vectorstore.create(
            chunks
        )

        LOGGER.info(
            "Knowledge base created successfully."
        )

    def ask(
        self,
        question: str,
        session_id: str = "default"
    ):

        LOGGER.info(
            "Processing user question for session: %s",
            session_id
        )

        try:

            # =================================
            # 1. VALIDATE QUESTION
            # =================================

            safe_question = (
                self.guardrails
                .validate_question(
                    question
                )
            )

            # =================================
            # 2. GET SESSION MEMORY
            # =================================

            memory = (
                self.session_memory.get(
                    session_id=session_id
                )
            )

            if memory:

                LOGGER.debug(
                    "Session memory available for %s.",
                    session_id
                )

            else:

                LOGGER.debug(
                    "No previous session memory for %s.",
                    session_id
                )

            # =================================
            # 3. LOAD VECTOR DATABASE
            # =================================

            database = (
                self.vectorstore.load()
            )

            # =================================
            # 4. RETRIEVE
            # =================================

            retriever = Retriever(
                vectorstore=database,
                k=settings.retrieval_k
            )

            retrieved = (
                retriever.retrieve(
                    safe_question
                )
            )

            if not retrieved:

                answer = (
                    "The provided study material "
                    "does not contain enough "
                    "information to answer this "
                    "accurately."
                )

                # Still update memory because
                # the conversation happened.
                self.session_memory.update(
                    user_message=safe_question,
                    assistant_response=answer,
                    session_id=session_id
                )

                return answer

            # =================================
            # 5. RERANK
            # =================================

            documents = (
                self.reranker.rerank(
                    query=safe_question,
                    documents=retrieved,
                    top_k=settings.rerank_top_k
                )
            )

            if not documents:

                answer = (
                    "The provided study material "
                    "does not contain enough "
                    "information to answer this "
                    "accurately."
                )

                self.session_memory.update(
                    user_message=safe_question,
                    assistant_response=answer,
                    session_id=session_id
                )

                return answer

            # =================================
            # 6. BUILD CONTEXT
            # =================================

            context = "\n\n".join(
                document.page_content
                for document in documents
            )

            # =================================
            # 7. GENERATE ANSWER
            # =================================

            answer = self.llm.generate(
                question=safe_question,
                context=context,
                session_memory=memory
            )

            # =================================
            # 8. UPDATE SESSION MEMORY
            # =================================

            self.session_memory.update(
                user_message=safe_question,
                assistant_response=answer,
                session_id=session_id
            )

            LOGGER.info(
                "Question completed successfully for session: %s",
                session_id
            )

            return answer

        except GuardrailViolation as exc:

            LOGGER.warning(
                "Guardrail blocked request: %s",
                exc
            )

            return (
                "I couldn't process that request. "
                f"{exc}"
            )

        except Exception:

            LOGGER.exception(
                "Unexpected pipeline error."
            )

            return (
                "I encountered an unexpected error "
                "while processing your request."
            )

    def clear_memory(self, session_id: str | None = None):

        LOGGER.info(
            "Clearing session memory for: %s",
            session_id or "all"
        )

        self.session_memory.clear(session_id=session_id)

    def get_memory(self, session_id: str = "default"):

        return self.session_memory.get(session_id=session_id)