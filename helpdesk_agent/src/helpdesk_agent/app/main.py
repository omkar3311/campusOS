from __future__ import annotations

from dotenv import load_dotenv

from helpdesk_agent.agent import (
    HelpdeskGraph,
)
from helpdesk_agent.guardrails import (
    GuardrailViolation,
)
from helpdesk_agent.logger import (
    LOGGER,
)


load_dotenv()


def create_helpdesk_graph() -> HelpdeskGraph:

    LOGGER.info(
        "Initializing Helpdesk Agent."
    )

    graph = HelpdeskGraph()

    LOGGER.info(
        "Helpdesk Agent initialized successfully."
    )

    return graph


def run() -> None:

    LOGGER.info(
        "Starting College Helpdesk Agent."
    )

  
    graph = create_helpdesk_graph()

    session_id = "cli-session"

    print()
    print(
        "College Helpdesk Agent"
    )
    print(
        "Agent ready."
    )
    print(
        "Type 'exit' to quit."
    )

    while True:

        try:

            question = input(
                "\nYou: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):

            print(
                "\nGoodbye."
            )

            break

        if question.lower() in {
            "exit",
            "quit",
        }:

            print(
                "Goodbye."
            )

            break

        if not question:

            continue

        try:

            result = graph.invoke(
                question=question,
                session_id=session_id,
            )

            answer = result.get(
                "answer",
                "I could not generate a response.",
            )

            print(
                f"\nHelpdesk: {answer}"
            )

            sources = result.get(
                "sources",
                [],
            )

            if sources:

                print(
                    "\nSources:"
                )

                for source in dict.fromkeys(
                    sources
                ):

                    print(
                        f"- {source}"
                    )

        except GuardrailViolation as exc:

            LOGGER.warning(
                "Request blocked: %s",
                exc,
            )

            print(
                f"\nHelpdesk: {exc}"
            )

        except Exception:

            LOGGER.exception(
                "Unhandled application error."
            )

            print(
                "\nHelpdesk: Sorry, "
                "something went wrong while "
                "processing your question."
            )


def main() -> None:

    run()


if __name__ == "__main__":

    main()