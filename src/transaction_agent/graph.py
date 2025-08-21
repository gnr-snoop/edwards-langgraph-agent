import os
import asyncio
from contextlib import asynccontextmanager
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from langchain.chat_models import init_chat_model
from transaction_agent.prompts.clickup_agent_prompt import QMS_ASSISTANT_PROMPT, HRM_ASSISTANT_PROMPT

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

from dotenv import load_dotenv
load_dotenv()

model = init_chat_model("azure_openai:gpt-4.1", temperature=0)

_available_tools = (
        "create_task", 
        "update_task",
        "get_task"
    )


def get_transaction_info(transaction_type: str) -> tuple[int, str]:
    if transaction_type == "qms":
        return QMS_ASSISTANT_PROMPT, 901409098158, "qms"
    elif transaction_type == "hrm":
        return HRM_ASSISTANT_PROMPT, 901409005728, "hrm"
    else:
        raise ValueError(f"Unsupported transaction type: {transaction_type}")


# Make the graph with MCP context
async def make_graph(transaction_type, mcp_host: str = "http://localhost:10000/mcp/", ) -> StateGraph:
    client = MultiServerMCPClient(
        {
            "clickup": {
                "url": mcp_host,
                "transport": "streamable_http",
            }
        }
    )
    mcp_tools = await client.get_tools()
    mcp_tools = [tool for tool in mcp_tools if tool.name in _available_tools]

    custom_fields_prompt = await client.get_prompt("clickup", "custom_fields")
    users_prompt = await client.get_resources("clickup", uris=["bigquery://projects/Snoop-RAG/datasets/findings/tables/resource_clickup_user"])
    
    prompt_template, list_id, form_id = get_transaction_info(transaction_type)
    form = await client.get_resources("clickup", uris=[f"file://forms/{form_id}"])
    list_id = list_id
    prompt = prompt_template.format(
        LIST_ID=list_id, 
        CUSTOM_FIELDS_PROMPT=custom_fields_prompt[0].content,
        CLICKUP_USERS=users_prompt[0].data,
        FORM=form[0].data
    )

    print(f"Available tools: {[tool.name for tool in mcp_tools]}")
    
    llm_with_tool = model.bind_tools(mcp_tools)

    def call_model(state: State):
        response = llm_with_tool.invoke([SystemMessage(prompt)] + state["messages"])
        return {"messages": [response]}

    # Compile application and test
    graph_builder = StateGraph(State)
    graph_builder.add_node(call_model)
    graph_builder.add_node("tool", ToolNode(mcp_tools))

    graph_builder.add_edge(START, "call_model")

    # Decide whether to retrieve
    graph_builder.add_conditional_edges(
        "call_model",
        # Assess agent decision
        tools_condition,
        {
            # Translate the condition outputs to nodes in our graph
            "tools": "tool",
            END: END,
        },
    )
    graph_builder.add_edge("tool", "call_model")

    graph = graph_builder.compile()
    graph.name = "Tool Agent"

    return graph

# Run the graph with question
async def main():

    graph = await make_graph("hrm", "http://localhost:10000/mcp/")
    result = await graph.ainvoke({"messages": "Quiero cargar un hallazgo"})
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())