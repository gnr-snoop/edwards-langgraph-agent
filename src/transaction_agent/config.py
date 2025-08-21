import os
from typing import Any, Optional
from dataclasses import dataclass, fields

from langgraph.config import get_config


@dataclass(kw_only=True)
class Configuration:
    """The Configuration fields for the agent."""

    mcp_host = "http://localhost:10000"
    available_tools = (
        "create_task", 
        "update_task",
        "get_task"
    )
    list_id = 901409098158
    form = "qms"


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