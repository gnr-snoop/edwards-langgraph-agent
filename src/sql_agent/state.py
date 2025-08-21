from langgraph.graph import MessagesState

class SQLAgentState(MessagesState):
    counter: int
    input: str
    list_tables_tool: object = None
    get_schema_tool: object = None
    db_query_tool: object = None

class SQLOutputState(MessagesState):
    answer: str