from langgraph.graph import MessagesState

from typing import List

class State(MessagesState):
    """Simple state."""
    next: List[str]
    sources: str
    links: str
    user_email: str