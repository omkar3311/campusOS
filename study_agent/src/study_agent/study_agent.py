from study_agent.logger import LOGGER
from study_agent.pipeline import RAGPipeline


class StudyAgent:

    def __init__(self):

        LOGGER.info(
            "Creating Study Agent."
        )

        self.pipeline = RAGPipeline()

    def display_header(self):

        LOGGER.info(
            "\n%s",
            "=" * 55
        )

        LOGGER.info(
            "           STUDENT RAG ASSISTANT"
        )

        LOGGER.info(
            "%s",
            "=" * 55
        )

        LOGGER.info(
            "Study Planning | Assignment Help | Quiz Generation"
        )

        LOGGER.info(
            "Commands: 'clear' | 'memory' | 'exit'"
        )

    def initialize(self):

        LOGGER.info(
            "Initializing knowledge base."
        )

        try:

            self.pipeline.build_database()

        except Exception:

            LOGGER.exception(
                "Knowledge base initialization failed."
            )

            return False

        return True

    def get_question(self):

        try:

            return input(
                "\nWhat do you want help with?\n> "
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt
        ):

            LOGGER.info(
                "CLI interrupted."
            )

            return "exit"

    def run(self):

        LOGGER.info(
            "Starting Study Agent."
        )

        self.display_header()

        if not self.initialize():

            LOGGER.error(
                "Study Agent could not start."
            )

            return

        while True:

            question = self.get_question()

            if not question:

                LOGGER.warning(
                    "Empty question received."
                )

                continue

            command = question.lower()

            # =================================
            # EXIT
            # =================================

            if command in {
                "exit",
                "quit",
                "q"
            }:

                LOGGER.info(
                    "Shutting down Study Agent."
                )

                break

            # =================================
            # CLEAR MEMORY
            # =================================

            if command == "clear":

                self.pipeline.clear_memory()

                LOGGER.info(
                    "Session memory cleared."
                )

                print(
                    "\nSession memory cleared."
                )

                continue

            # =================================
            # SHOW MEMORY
            # =================================

            if command == "memory":

                memory = (
                    self.pipeline.get_memory()
                )

                print(
                    "\nSession Memory:"
                )

                print(
                    memory
                    or "No session memory."
                )

                continue

            # =================================
            # NORMAL QUESTION
            # =================================

            answer = self.pipeline.ask(
                question
            )

            LOGGER.info(
                "\n%s",
                "=" * 55
            )

            LOGGER.info(
                "ANSWER"
            )

            LOGGER.info(
                "%s",
                "=" * 55
            )

            LOGGER.info(
                "\n%s",
                answer
            )


def main():

    agent = StudyAgent()

    agent.run()


if __name__ == "__main__":

    main()