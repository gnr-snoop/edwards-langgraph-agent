"""Define the configurable parameters for the chat bot."""

import os
from dataclasses import dataclass, fields
from typing import Any, Optional
from langgraph.store.base import Item

from langgraph.config import get_config

def format_memories(memories: Optional[list[Item]]) -> str:
    """Format the user's memories."""
    if not memories:
        return ""
    # Note Bene: You can format better than this....
    formatted_memories = "\n".join(
        f"{str(m.value)}\tLast updated: {m.updated_at}" for m in memories
    )
    return f"""

## Memories

You have noted the following memorable events from previous interactions with the user.
<memories>
{formatted_memories}
</memories>
"""

@dataclass(kw_only=True)
class ChatConfigurable:
    """The configurable fields for the chatbot."""

    user_id: str = "default-user"
    mem_assistant_id: str = (
        "memory_graph"  # update to the UUID if you configure a custom assistant
    )
    delay_seconds: int = 30  # For debouncing memory creation
    memory_types: Optional[list[dict]] = None
    """The memory_types for the memory assistant."""

    @classmethod
    def from_context(cls) -> "ChatConfigurable":
        """Create a ChatConfigurable instance from a RunnableConfig object."""
        try:
            config = get_config()
            configurable = (
                config["configurable"] if config and "configurable" in config else {}
            )
        except RuntimeError:
            configurable = {}

        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in values.items() if v})