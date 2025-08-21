import asyncio
from typing import Literal
from langgraph.graph import StateGraph

from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, FewShotPromptTemplate, PromptTemplate
from langchain_core.example_selectors import SemanticSimilarityExampleSelector

from sql_agent.sql_db import get_sqlalchemy_engine
from sql_agent.state import SQLAgentState, SQLOutputState
from sql_agent.tools import SubmitFinalAnswer, GenerateQuery, create_tool_node_with_fallback, setup_tools

from sql_agent.prompts.sql_agent_few_shot import examples
from sql_agent.prompts.sql_agent_prompt import QUERY_CHECK_SYSTEM, GENERATE_MSG_SYSTEM, QUERY_GEN_SYSTEM, MODEL_GET_SCHEMA_SYSTEM


from langchain_core.runnables import RunnableConfig
from sql_agent.config import Configuration
from langgraph.graph import StateGraph
from langgraph_sdk import get_client
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

RETRY_LIMIT = 3

llm = init_chat_model("azure_openai:gpt-4.1", temperature=0)
embeddings_model = init_embeddings("azure_openai:embedding-test")
db = get_sqlalchemy_engine("postgres")
list_tables_tool, get_schema_tool, db_query_tool = setup_tools(db, llm)

async def retry_limit_node(state: SQLAgentState) -> SQLOutputState:

    return {
        #"messages": [AIMessage(content="No se han encontrado resultados. Por favor, ingrese su consulta nuevamente.")]
        "answer": "No se han encontrado resultados. Por favor, ingrese su consulta nuevamente."
    }

async def list_tables(state: SQLAgentState):
    tool_call = {
        "name": "sql_db_list_tables",
        "args": {},
        "id": "abc123",
        "type": "tool_call",
    }
    tool_message = list_tables_tool.invoke(tool_call)
    response = AIMessage(f"Available tables: {tool_message.content}")

    return {"messages": [response]}

async def get_schema(state: SQLAgentState):
    """
    Calls the get_schema tool using the LLM and returns the database schema as an AIMessage.
    """
    # Force a model to create a tool call
    model = llm.bind_tools([get_schema_tool])
    messages = [SystemMessage(MODEL_GET_SCHEMA_SYSTEM)] + state["messages"]
    llm_response = await model.ainvoke(messages)

    # Defensive: Ensure tool_calls exist and are valid
    tool_call = llm_response.tool_calls[0] if getattr(llm_response, "tool_calls", None) else None
    if not tool_call:
        return {"messages": [AIMessage(content="Error: No tool call returned for schema retrieval.")]}

    # Call the get_schema tool directly
    schema_result = await get_schema_tool.ainvoke(tool_call)
    schema_message = AIMessage(content=f"Database schema: {schema_result.content}")
    return {"messages": [schema_message]}


async def query_gen(state: SQLAgentState):
    example_selector = await SemanticSimilarityExampleSelector.afrom_examples(
        examples,
        embeddings_model,
        FAISS,
        k=3,
        input_keys=["input"],
    )

    few_shot_prompt = FewShotPromptTemplate(
        example_selector=example_selector,
        example_prompt=PromptTemplate.from_template(
            "User input: {input}\nSQL query: {query}"
        ),    
        input_variables=["input"],
        prefix=QUERY_GEN_SYSTEM,
        suffix="",
    )

    query_gen_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate(prompt=few_shot_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("messages"),
        ]
    )
    query_gen = query_gen_prompt | llm.with_structured_output(GenerateQuery)
    message = await query_gen.ainvoke(state)

    return {
        "messages": [message.query]
    }

async def check_query(state: SQLAgentState):
    """
    Use this tool to double-check if your query is correct before executing it.
    """
    query_check_prompt = ChatPromptTemplate.from_messages(
        [("system", QUERY_CHECK_SYSTEM), ("placeholder", "{messages}")]
    )
    query_check = query_check_prompt | llm.bind_tools([db_query_tool], tool_choice="required")
    # Check only the last message in the state, wich contains the generated query
    response = await query_check.ainvoke({"messages": [state["messages"][-1]]})
    return {
        "messages": [response],
        "counter": state["counter"] + 1,
    }

    
async def execute_query(state: SQLAgentState):
    return create_tool_node_with_fallback([db_query_tool])

async def generate_msg_node(state: SQLAgentState) -> SQLOutputState:

    generate_msg_prompt = ChatPromptTemplate.from_messages(
        [("system", GENERATE_MSG_SYSTEM), ("placeholder", "{messages}")]
    )
    generate_msg = generate_msg_prompt | llm.with_structured_output(SubmitFinalAnswer)
    message = await generate_msg.ainvoke(state)

    print(f"Final answer: {message.final_answer}")
    print("***"*10)
    return {
        #"messages": [AIMessage(content=message.final_answer)]
        "answer": message.final_answer
    }

async def should_continue(state: SQLAgentState) -> Literal["query_gen", "retry_limit", "final_answer"]:
    if state["messages"][-1].content.startswith("Error:"):
        if state["counter"] < RETRY_LIMIT: 
            return "query_gen"
        else:
            return "retry_limit"
    return "final_answer"


workflow = StateGraph(SQLAgentState, config_schema=Configuration, output=SQLOutputState)


workflow.add_node("list_tables", list_tables)
workflow.add_node("get_schema", get_schema)
workflow.add_node("query_gen", query_gen)
workflow.add_node("check_query", check_query)
workflow.add_node("execute_query", execute_query)
workflow.add_node("final_answer", generate_msg_node)
workflow.add_node("retry_limit", retry_limit_node)

#workflow.set_entry_point("init_db")
#workflow.add_edge("init_db", "list_tables")
workflow.set_entry_point("list_tables")
workflow.add_edge("list_tables", "get_schema")
workflow.add_edge("get_schema", "query_gen")
workflow.add_edge("query_gen", "check_query")
workflow.add_edge("check_query", "execute_query")
workflow.add_conditional_edges(
    "execute_query",
    should_continue
)

graph = workflow.compile(checkpointer=None)