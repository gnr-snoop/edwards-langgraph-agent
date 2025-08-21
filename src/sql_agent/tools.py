from typing import Any
from pydantic import BaseModel, Field

from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit



class SubmitFinalAnswer(BaseModel):
    """Submit the final answer to the user based on the query results."""
    final_answer: str = Field(..., description="The final answer to the user, including the sql query that got such answer.")


class GenerateQuery(BaseModel):
    """Generate the BigQuery query."""

    query: str = Field(..., description="The query")

def create_tool_node_with_fallback(tools: list) -> RunnableWithFallbacks[Any, dict]:
    """
    Create a ToolNode with a fallback to handle errors and surface them to the agent.
    """
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }


def setup_tools(db, llm):

    @tool
    def db_query_tool(query: str):
        """
        Execute a SQL query against the database and get back the result.
        If the query is not correct, an error message will be returned.
        If an error is returned, rewrite the query, check the query, and try again.
        """
        result = db.run_no_throw(query)
        if not result:
            return "Result is empty."
            #"Error: Query failed. Please rewrite your query and try again."
        return result

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()

    # retriever
    """
    def query_as_list(db, query):
        res = db.run(query)
        res = [el for sub in ast.literal_eval(res) for el in sub if el]
        res = [re.sub(r"\b\d+\b", "", string).strip() for string in res]
        return list(set(res))

    users = query_as_list(db, "SELECT CONCAT(first_name, ' ', last_name) FROM user")
    areas = query_as_list(db, "SELECT DISTINCT areas FROM task")
    status = query_as_list(db, "SELECT DISTINCT status FROM task")
    types = query_as_list(db, "SELECT DISTINCT tipo_hallazgo FROM task")

    embeddings_mmodel = EmbeddingsModelFactory.create_embeddings_model("azure_openai")
    vector_store = VectorSearchFactory.create_vectorial_instance(
        provider="in_memory",
        index_name="proper_nouns",
        embedding_model=embeddings_mmodel
    )
    vector_store.add_texts(users + areas + status + types)
    retriever = vector_store.as_retriever(search_kwargs={"k": 1})
    description = (
        "Use to look up values to filter on. Input is an approximate spelling "
        "of the proper noun, output is valid proper nouns. Use the noun most "
        "similar to the search."
    )
    retriever_tool = create_retriever_tool(retriever, name="search_proper_nouns", description=description)
    """

    list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
    get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

    #return retriever_tool, list_tables_tool, get_schema_tool, db_query_tool
    return list_tables_tool, get_schema_tool, db_query_tool