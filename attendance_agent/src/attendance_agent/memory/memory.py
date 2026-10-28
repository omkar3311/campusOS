from langgraph.checkpoint.memory import InMemorySaver


class AttendanceMemory:
    """
    Conversation memory for the attendance agent.

    Memory exists for the lifetime of the application.
    """

    def __init__(self):
        self.checkpointer = InMemorySaver()

    def config(
        self,
        session_id: str,
    ) -> dict:
        """
        Return LangGraph configuration
        for a conversation session.
        """

        return {
            "configurable": {
                "thread_id": session_id,
            }
        }