from typing import List
from dataclasses import dataclass
from langgraph.graph import MessagesState
#from entities.user.user import User
from rag_agent.document import Document



class RagState(MessagesState):
    documents: List[Document]
    question: str
    generation: str
    sources: str
    links: str
    retry_count_grade_documents: int = 1
    retry_count_hallucinations: int = 3
    error: bool
    error_message: str
    domain: str
    storage_service: str
    reflection: bool
