from typing import Literal

from langchain import hub
from langchain.embeddings import init_embeddings
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langgraph.graph import StateGraph
from langgraph.types import Command

from rag_agent.state import RagState
from rag_agent.tools import GradeDocuments, GradeHallucinations, GradeAnswer
from rag_agent.errors import DECIDE_TO_GENERATE_ERROR, NO_DOCUMENTS_FOR_QUESTION_ERROR, HALLUCINATION_ERROR
from rag_agent.storage_services import StorageServiceFactory
from rag_agent.config import Configuration

from rag_agent.prompts.adaptative_rag_agent_prompt import GRADE_DOCUMENTS_PROMPT, GRADE_HALLUCINATIONS_PROMPT, GRADE_ANSWER_PROMPT, TRANSFORM_QUERY_PROMPT
from rag_agent.vector_stores.vectorial_db import VectorSearchFactory


generation_llm = init_chat_model("azure_openai:gpt-4.1-mini", temperature=0)
reflection_llm = init_chat_model("azure_openai:gpt-4.1-mini", temperature=0)
#reflection_llm = init_chat_model("gemini:gemini-2.0-flash", temperature=0) #langchain_google_vertexai
embedding_model = init_embeddings("azure_openai:embedding-test")

async def retrieve(state: RagState):

    agent_config = Configuration.from_context()
    user_email = agent_config.user_email
    provider = agent_config.provider
    index_name = agent_config.index_name
    storage_service_type = agent_config.storage_service_type
    query = state["messages"][-1].content

    # TODO: Add auth and validation in retrieval stage
    retriever = VectorSearchFactory.create_vectorial_instance(provider, index_name, embedding_model)
    documents = await retriever.retrieve(query)  
    #storage_service = StorageServiceFactory.create_storage_service_instance(storage_service_type)
    #documents = storage_service.validate_permissions(documents, user_email)           
    return {"documents": documents, "question": query}

async def grade_documents(state: RagState):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with only filtered relevant documents
    """
    question = state["question"]
    documents = state["documents"]

    filtered_docs = []
    
    structured_llm_grader = reflection_llm.with_structured_output(GradeDocuments)

    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", GRADE_DOCUMENTS_PROMPT),
            ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
        ]   
    )
    retrieval_grader = grade_prompt | structured_llm_grader

    for doc in documents:
        score = await retrieval_grader.ainvoke(
            {"question": question, "document": doc.content}
        )
        grade = score.binary_score
        if grade == "yes":
            filtered_docs.append(doc)
        else:
            continue

    return {"documents": filtered_docs, "question": question}

async def decide_to_generate(state: RagState) -> Command[Literal["printer", "transform_query", "generate"]]:
    """
    Determines whether to generate an answer, or re-generate a question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    state["question"]
    filtered_documents = state["documents"]

    retry_count_grade_documents = state["retry_count_grade_documents"]
    error = False
    error_message = None
    if retry_count_grade_documents == 0:
        goto = "printer",
        error = True
        error_message = DECIDE_TO_GENERATE_ERROR
    elif not filtered_documents:
        retry_count_grade_documents = retry_count_grade_documents - 1
        goto = "transform_query"
    else:
        goto = "generate"
    return Command(
        goto=goto,
        update={
            "error": error,
            "retry_count_grade_documents": retry_count_grade_documents,
            "error_message": error_message if error_message is not None else ""
        }
    )

async def generate(state: RagState) -> Command[Literal["printer", "generate"]]:
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    question = state["question"]
    documents = state["documents"]
    prompt = hub.pull("rlm/rag-prompt")
    rag_chain = prompt | generation_llm | StrOutputParser()

    generation = await rag_chain.ainvoke({"context": " ".join([doc.content for doc in documents]), "question": question})
    return {"documents": documents, "question": question, "generation": generation}

async def reflection_validator(state: RagState):
    if state["reflection"]:
        return "grade_generation_v_documents_and_question"
    else:
        return "printer"

async def grade_generation_v_documents_and_question(state: RagState):
    """
    Determines whether the generation is grounded in the document and answers question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Decision for next node to call
    """
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    hallucination_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", GRADE_HALLUCINATIONS_PROMPT),
            ("human", f"Set of facts: \n\n {' '.join([doc.content for doc in documents])} \n\n LLM generation: {generation}"),
        ]
    )

    structured_llm_grader = reflection_llm.with_structured_output(GradeHallucinations)
    hallucination_grader = hallucination_prompt | structured_llm_grader
    score = await hallucination_grader.ainvoke(
        {"documents": documents, "generation": generation}
    )
    grade = score.binary_score

    error = False
    error_message = None
    retry_count_hallucinations = state["retry_count_hallucinations"]

    if grade == "yes": # not an hallucination
        structured_llm_grader = reflection_llm.with_structured_output(GradeAnswer)

        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", GRADE_ANSWER_PROMPT),
                ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
            ]
        )

        answer_grader = answer_prompt | structured_llm_grader
        score = await answer_grader.ainvoke({"question": question, "generation": generation})
        grade = score.binary_score

        if grade == "yes":
            goto = "printer"
        else:
            error = True
            error_message = NO_DOCUMENTS_FOR_QUESTION_ERROR
            goto = "printer"
    else: # hallucination
        if retry_count_hallucinations == 0:
            error_message = HALLUCINATION_ERROR
            goto = "printer",
            error = True
        else:
            retry_count_hallucinations = retry_count_hallucinations - 1
            goto = "generate"
    return Command(
        goto=goto,
        update={
            "error": error,
            "retry_count_hallucinations": retry_count_hallucinations,
            "error_message": error_message if error_message is not None else ""
        }
    )
    
async def transform_query(state: RagState):
    """
    Transform the query to produce a better question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates question key with a re-phrased question
    """
    question = state["question"]
    documents = state["documents"]

    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TRANSFORM_QUERY_PROMPT),
            (
                "human",
                "Here is the initial question: \n\n {question} \n Formulate an improved question.",
            ),
        ]
    )

    question_rewriter = re_write_prompt | generation_llm | StrOutputParser()
    better_question = await question_rewriter.ainvoke({"question": question})

    return {"documents": documents, "question": better_question}
    
async def printer(state: RagState):
    if(state["error"]):
        error = state["error_message"]
        return {"messages": [error]}
    else:
        documents = state['documents']
        generation = state['generation']
        sources = [doc.filename for doc in documents]
        links = [doc.source for doc in documents]
        return {
            "messages": generation,
            "sources": sources,
            "links": links
        }

workflow = StateGraph(RagState, config_schema=Configuration)
workflow.add_node("retrieve", retrieve)  
workflow.add_node("grade_documents", grade_documents)  
workflow.add_node("decide_to_generate", decide_to_generate)
workflow.add_node("generate", generate)
#workflow.add_node("grade_generation_v_documents_and_question", grade_generation_v_documents_and_question)
workflow.add_node("transform_query", transform_query)  
workflow.add_node("printer", printer)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_edge("transform_query", "retrieve")
workflow.add_edge("grade_documents", "decide_to_generate")
workflow.add_conditional_edges("generate", reflection_validator)

graph = workflow.compile(checkpointer=None)