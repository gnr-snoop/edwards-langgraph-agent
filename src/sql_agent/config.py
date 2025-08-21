import os
from typing import Any, Optional
from dataclasses import dataclass, fields

from langgraph.config import get_config


@dataclass(kw_only=True)
class Configuration:
    """The Configuration fields for the agent."""

    user_id: str = "1"
    mem_assistant_id: str = (
        "memory_graph"  # update to the UUID if you configure a custom assistant
    )
    delay_seconds: int = 300  # For debouncing memory creation
    """The memory_types for the memory assistant."""
    memory_types: Optional[list[dict]] = None
    domain: str = "postgres"  # The type of database to connect to

    @classmethod
    def from_context(cls) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig object."""
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