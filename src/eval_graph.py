from dotenv import load_dotenv
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client
import os, requests
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage

from graph.agent import MainGraph
from models.chat_models import models

load_dotenv()


LANGCHAIN_END = os.getenv('LANGCHAIN_END')
LANGCHAIN_API = os.getenv('LANGCHAIN_API')
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv('AZURE_OPENAI_CHATGPT_DEPLOYMENT')
langchain_client = Client(api_url=LANGCHAIN_END, api_key=LANGCHAIN_API)

checkpointer = MemorySaver()
graph = MainGraph(checkpointer)

def create_dataset(dataset_name, csv_path, csv_file):
    print("Creando dataset")
    # Variables del .csv
    input_keys = ['ID', 'Pregunta', 'Thread_id']
    output_keys = ['Respuesta']   

    try:
        datasets = list(langchain_client.list_datasets(dataset_name=dataset_name))
        if datasets:
            raise ValueError("No se pudo crear el dataset porque ya existe uno con ese nombre")
        else:
            langchain_client.upload_csv(
                csv_file = f"{csv_path}/{csv_file}",
                input_keys = input_keys,
                output_keys = output_keys,
                name = dataset_name,
                description = "Dataset created from a CSV file",
                data_type = "kv"
            )
    except ValueError as e:
        print(e)

class Grade(BaseModel):
  score: bool = Field(
      description="Boolean that indicates whether the response is accurate relative to the reference answer"
  )

def accuracy(outputs: dict, reference_outputs: dict) -> bool:
    #instructions = """Evaluate Student Answer against Ground Truth for conceptual similarity and classify true or false: 
    #- False: No conceptual match and similarity
    #- True: Most or full conceptual match and similarity
    #- Key criteria: Concept should match, not exact wording.
    #"""

    instructions = """Instructions:

    Compare two BigQuery queries (student query and ground truth query) to determine if they serve the same purpose or are logically equivalent. Classify the result as True or False:

    - False: The queries do not serve the same purpose or are not equivalent.
    - True: The queries serve the same purpose or are logically equivalent in terms of their result.

    Key criteria for comparison:

    1. The queries should be nearly equivalent in terms of the result they produce, regardless of minor differences in the SELECT clause, such as column order or table aliases.
    2. Consider transformations and functions used in the queries, as long as both produce the same logical result.
    3. The queries may differ in syntax details or structure, but they should return the same data or results when executed.

    Suggestions:

    - Compare the FROM, WHERE, GROUP BY, HAVING, ORDER BY, and JOIN clauses to determine if the underlying logic of the query is equivalent.
    - Ignore minor differences in presentation, such as the use of aliases or line breaks, but ensure that the operations and conditions are functionally similar.    
    """

    response = models["edwards"].with_structured_output(Grade).invoke(
        [
            { "role": "system", "content": instructions },
            {
                "role": "user",
                "content": f"""Ground Truth query: {reference_outputs["Respuesta"]}; 
                Student's query: {outputs["response"]}"""
            },
        ],
    )

    return response.score

def simple(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["response"] == reference_outputs["Respuesta"]

def target(inputs: dict) -> dict:

    try:
        response = graph.invoke(HumanMessage(content=inputs["Pregunta"]), thread_id=inputs["Thread_id"]) 
        assistant_response = response
    except requests.exceptions.RequestException as e:
        assistant_response = "Hubo un error al obtener respuesta del bot."
    return { 
        "response": assistant_response
    }


class Query(BaseModel):

    """
    Extract the sql query from the response. Just include the following details:

    - query: The query extracted from the response.

    If any required field is missing or contains invalid data, set the field to `None`.
    """

    query: Optional[str] = Field(..., description="BigQuery SQL Query.")


def target_bigquery(inputs: dict) -> dict:

    try:
        response = graph.invoke(HumanMessage(content=inputs["Pregunta"]), thread_id=inputs["Thread_id"])["message"]
        message = HumanMessage(content=response)
        query = models["big_query"].with_structured_output(Query).invoke([message]).query
        assistant_response = query if query is not None else "Query not found."
    except requests.exceptions.RequestException as e:
        assistant_response = "Hubo un error al obtener respuesta del bot."
    return { 
        "response": assistant_response
    }

def target_supervisor(inputs: dict) -> dict:

    try:
        response = graph.invoke(HumanMessage(content=inputs["Pregunta"]), thread_id=inputs["Thread_id"]) 
        assistant_response = response
    except requests.exceptions.RequestException as e:
        assistant_response = "Hubo un error al obtener respuesta del bot."
    return { 
        "response": assistant_response['agent']
    }

def evaluate(dataset_name, metric):

    print("Evaluando...")

    examples = list(langchain_client.list_examples(dataset_name=dataset_name))
    examples.sort(key=lambda example: example.inputs["ID"], reverse=False)

    langchain_client.evaluate(
        targets["supervisor"],
        data=examples,
        evaluators=[
            metric,
        ],
        experiment_prefix="bigquery_evaluation",
        max_concurrency=1,
    )

targets = {
    "supervisor": target_supervisor,
    "bigquery": target_bigquery,
    "other": target
}

csv_path = 'test_cases'
"""
# rag testcases
dataset_name = "edwards_test_cases_rag"
csv_file = 'rag_test_cases.csv'
create_dataset(dataset_name, csv_path, csv_file)
evaluate(dataset_name, accuracy)
"""

# supervisor testcases
dataset_name = "edwards_test_cases_supervisor"
csv_file = 'supervisor_test_cases.csv'
create_dataset(dataset_name, csv_path, csv_file)
evaluate(dataset_name, simple)


"""
# bigquery testcases
dataset_name = "edwards_test_cases_bigquery"
csv_file = 'bigquery_test_cases.csv'
create_dataset(dataset_name, csv_path, csv_file)
evaluate(dataset_name, accuracy)
"""
