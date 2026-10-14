import logging

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
)


LOGGER = logging.getLogger(__name__)


class AgentLogger:

    @staticmethod
    def debug_agent_response(response: dict) -> None:

        print("\n" + "=" * 80)
        print("AGENT EXECUTION")
        print("=" * 80)

        for message in response.get("messages", []):

            if isinstance(message, HumanMessage):
                print("\n🧑 USER")
                print("-" * 80)
                print(message.content)

            elif isinstance(message, AIMessage):

                if message.tool_calls:
                    print("\n🤖 TOOL CALLS")
                    print("-" * 80)

                    for i, tool in enumerate(
                        message.tool_calls,
                        start=1,
                    ):
                        print(
                            f"[{i}] Tool : {tool['name']}"
                        )
                        print(
                            f"    Args : {tool['args']}"
                        )

                else:
                    print("\n🤖 FINAL ANSWER")
                    print("-" * 80)
                    print(message.content)

            elif isinstance(message, ToolMessage):
                print("\n🔧 TOOL RESPONSE")
                print("-" * 80)
                print(
                    f"Tool : {message.name}"
                )
                print(message.content)

        print("=" * 80)