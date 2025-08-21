import json
from typing import Literal, TypedDict

from langgraph_sdk import get_client
from langchain_core.runnables import RunnableConfig

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import RetryPolicy

from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate

from supervisor.prompts.edwards_prompt import EDWARDS_BASE_PROMPT
from supervisor.prompts.supervisor_prompt import SUPERVISOR_PROMPT_TEMPLATE
from supervisor.prompts.rags_supervisor_prompt import RAGS_SUPERVISOR_PROMPT_TEMPLATE
from supervisor.prompts.clickup_supervisor_prompt import CLICKUP_SUPERVISOR_PROMPT_TEMPLATE

from supervisor.state import State
from rag_agent.graph import graph as rag_agent
#from sql_agent.graph import graph as sql_agent
from sql_agent.postgres_graph import graph as sql_agent
from transaction_agent.graph import make_graph as create_transaction_agent_graph

from supervisor.config import ChatConfigurable




supervisor_llm = init_chat_model("azure_openai:gpt-4.1-mini", temperature=0)
edwards_llm = init_chat_model("azure_openai:gpt-4.1-mini", temperature=0)
MEMBERS = ["SQL_AGENT", "CLICKUP_AGENT", "RAG_AGENT", "HELP_AGENT"]

class Router(TypedDict):
    next: Literal[tuple(MEMBERS)]


async def supervisor_node(state: State) -> State:
    """
    The supervisor node is a special node that receives all messages
    from the user and other nodes and routes them to the correct
    node. It is responsible for deciding which node should receive
    the message and for deleting the messages that are not needed
    anymore.

    Parameters
    ----------
    state : State
        The current state of the graph

    Returns
    -------
    State
        The updated state of the graph
    """

    # Get the list of messages. The first message is the
    # system prompt, the rest are the messages from the user
    messages = [
        {"role": "system", "content": SUPERVISOR_PROMPT_TEMPLATE.format(MEMBERS=", ".join(MEMBERS))},
    ] + state["messages"]


    response = await supervisor_llm.with_structured_output(Router).ainvoke(messages)
    next_ = response.get("next") or response.get("properties", {}).get("next")

    return {
        "summary": "",
        #"messages": delete_messages,
        "next": next_,
        "sources": None,
        "links": None,
    }


async def bigquery_node(state: State) -> State:
    """Run the BigQuery agent with the user's message as input."""
    config = {
        "domain": "bigquery"
    }

    input = {
        "counter": 0,
        "input": state["messages"][-1].content,
    }
    result = await sql_agent.ainvoke(input, config=config)

    return {
        "messages": result["messages"][-1].content,
        "sources": None,
        "links": None
    }

async def postgres_node(state: State) -> State:
    """Run the postgres agent"""
    config = {
        "domain": "postgres"
    }
    
    input = {
        "counter": 0,
        "input": state["messages"][-1].content,
    }
    result = await sql_agent.ainvoke(input, config=config)
    print(f"Result: {result}")
    return {
        "messages": result["answer"],
        "sources": None,
        "links": None
    }

async def clickup_mcp_node(state: State) -> State:

    MEMBERS = ["QMS_AGENT", "HRM_AGENT"]
    prompt = CLICKUP_SUPERVISOR_PROMPT_TEMPLATE.format(MEMBERS=", ".join(MEMBERS))

    messages = [
        {"role": "system", "content": prompt},
    ] + state["messages"]

    class ClickUpRouter(TypedDict):
        next: Literal["QMS_AGENT", "HRM_AGENT"]
    
    response = await supervisor_llm.with_structured_output(ClickUpRouter).ainvoke(messages)
    next_ = response.get("next") or response.get("properties", {}).get("next")
    if next_ == "QMS_AGENT":
        graph = await create_transaction_agent_graph("qms", mcp_host="http://localhost:10000/mcp/")
    else:
        graph = await create_transaction_agent_graph("hrm", mcp_host="http://localhost:10000/mcp/")

    response = await graph.ainvoke({"messages": state["messages"]})

    return{
            "messages": response["messages"]
        }

async def rag_node(state: State) -> State:
    """Invoke the RAGS supervisor agent with the user's message as input."""
    user_email = state["user_email"]
    MEMBERS = ["QMS_Document_Retriever", "Freshwork_Document_Retriever"]
    prompt = RAGS_SUPERVISOR_PROMPT_TEMPLATE.format(MEMBERS=", ".join(MEMBERS))

    class Router(TypedDict):
        next: Literal["QMS_Document_Retriever", "Freshwork_Document_Retriever"]

    messages = [
                {"role": "system", "content": prompt},
            ] + state["messages"]

    response = await supervisor_llm.with_structured_output(Router).ainvoke(messages)
    next_ = response.get("next") or response.get("properties", {}).get("next")
    if next_ == "QMS_Document_Retriever":
            config = {
                "user_email": user_email,
                "provider": "pinecone",
                "index_name": "edwards-sgc-testing",  # The name of the vector store index
                "storage_service_type": "drive"
            }
    else:
        config = {
            "user_email": user_email,
            "provider": "pinecone",
            "index_name": "edwards-freshworks-testing",  # The name of the vector store index
            "storage_service_type": "drive"
        }

    input = {
        "messages": state["messages"],
        "retry_count_grade_documents": 1,
        "retry_count_hallucinations": 3,
        "error": False,
        "reflection": False,
        "current_user": user_email
    }
    result = await rag_agent.ainvoke(input, config=config)
    return {
        "messages": result["messages"][-1].content,
        "sources": result.get("sources"),
        "links": result.get("links"),
        "next": result.get("next"),
    }
    
async def help_node(state: State) -> State:
    """Generate answer about assistant capabilities."""

    help_prompt = PromptTemplate.from_template(EDWARDS_BASE_PROMPT)
    with open('src/supervisor/agents_discovery.json', 'r') as agents_discovery_file:
        data = json.load(agents_discovery_file)
        capabilities = ""
        how_to = ""
        for i in range(len(data)):
            capabilities += f"{i+1}.{data[i]['name']}: {data[i]['description']}"
            for use_case in data[i]['how-to-use']:
                how_to += f"**User:** {use_case['query']}\n**Help Node: ** *{use_case['answer']}*\n\n"

    system_message = help_prompt.format(
        capabilities=capabilities,
        howto=how_to
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system") or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [system_message] + conversation_messages

    result = await edwards_llm.ainvoke(prompt)

    return {
        "messages": result.content,
        "sources": None,
        "links": None
    }

async def next_agent(state: State) -> Literal["SQL_AGENT", "CLICKUP_AGENT", "RAG_AGENT", "HELP_AGENT"]:
    return state["next"]

async def schedule_memories(state: State, config: RunnableConfig) -> None:
    """Prompt the bot to respond to the user, incorporating memories (if provided)."""
    configurable = ChatConfigurable.from_context()
    memory_client = get_client()
    await memory_client.runs.create(
                # We enqueue the memory formation process on the same thread.
                # This means that IF this thread doesn't receive more messages before `after_seconds`,
                # it will read from the shared state and extract memories for us.
                # If a new request comes in for this thread before the scheduled run is executed,
                # that run will be canceled, and a **new** one will be scheduled once
                # this node is executed again.
                thread_id=config["configurable"]["thread_id"],
                # This memory-formation run will be enqueued and run later
                # If a new run comes in before it is scheduled, it will be cancelled,
                # then when this node is executed again, a *new* run will be scheduled
                multitask_strategy="enqueue",
                # This lets us "debounce" repeated requests to the memory graph
                # if the user is actively engaging in a conversation. This saves us $$ and
                # can help reduce the occurrence of duplicate memories.
                after_seconds=configurable.delay_seconds,
                # Specify the graph and/or graph configuration to handle the memory processing
                assistant_id="memory_graph",
                input={"messages": state["messages"]},
                config={
                    "configurable": {
                        # Ensure the memory service knows where to save the extracted memories
                        "user_id": configurable.user_id,
                    },
                },
            )


workflow = StateGraph(State,  config_schema=ChatConfigurable)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("SQL_AGENT", postgres_node, retry=RetryPolicy(max_attempts=3))
workflow.add_node("CLICKUP_AGENT", clickup_mcp_node)
workflow.add_node("RAG_AGENT", rag_node)   
workflow.add_node("HELP_AGENT", help_node)
workflow.add_node("MEMORY_AGENT", schedule_memories)

workflow.add_edge(START, "Supervisor")
workflow.add_conditional_edges("Supervisor", next_agent)

workflow.add_edge("SQL_AGENT", "MEMORY_AGENT")
workflow.add_edge("CLICKUP_AGENT", "MEMORY_AGENT")
workflow.add_edge("RAG_AGENT", "MEMORY_AGENT")
workflow.add_edge("HELP_AGENT", "MEMORY_AGENT")

graph = workflow.compile()