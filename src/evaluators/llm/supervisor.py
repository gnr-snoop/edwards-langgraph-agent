from dotenv import load_dotenv
from langsmith import Client
import os, requests
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage, HumanMessage

from simple_llm_with_tools import invoke

load_dotenv()

BIGQUERY_TOOLS = set([ 'sql_db_list_tables', 'sql_db_schema', 'sql_db_query_checker', 'sql_db_query', 'search_proper_nouns' ])
FORMS_TOOLS = set([ 'Task', 'validate', 'request_feedback', 'send' ])
RAG_TOOLS = set([ 'quality_retriever' ])
FRESHWORK_TOOLS = set([ 'freshwork_retriever' ])
HELP_TOOLS = set([ 'help' ])


LANGCHAIN_END = os.getenv('LANGCHAIN_END')
LANGCHAIN_API = os.getenv('LANGCHAIN_API')
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv('AZURE_OPENAI_CHATGPT_DEPLOYMENT')
langchain_client = Client(api_url=LANGCHAIN_END, api_key=LANGCHAIN_API)


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


def simple(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["response"] == reference_outputs["Respuesta"]


def target(inputs: dict) -> dict:

    try:
        response, called_tools = invoke(inputs["Pregunta"])

        called_tools = set(called_tools)

        if called_tools <= BIGQUERY_TOOLS:
            assistant_response = "BIGQUERY_AGENT"
        elif called_tools <= FORMS_TOOLS:
            assistant_response = "FORMS_AGENT"
        elif called_tools == RAG_TOOLS:
            assistant_response = "RAG_Document_Retriever"
        elif called_tools == FRESHWORK_TOOLS:
            assistant_response = "Freshwork_Document_Retriever"
        elif called_tools == HELP_TOOLS:
            assistant_response = "HELP_AGENT"
        else:
            assistant_response = "Incorrect tool calling."

    except requests.exceptions.RequestException as e:
        assistant_response = "Hubo un error al obtener respuesta del bot."
    return { 
        "response": assistant_response
    }


def evaluate(dataset_name):

    print("Evaluando...")

    examples = list(langchain_client.list_examples(dataset_name=dataset_name))
    examples.sort(key=lambda example: example.inputs["ID"], reverse=False)

    langchain_client.evaluate(
        target,
        data=examples,
        evaluators=[
            simple,
        ],
        experiment_prefix="llm_supervisor_evaluation",
        max_concurrency=10,
        num_repetitions=10
    )


csv_path = 'test_cases'
dataset_name = 'llm_edwards_test_cases_supervisor'
csv_file = 'supervisor_test_cases.csv'
create_dataset(dataset_name, csv_path, csv_file)
evaluate(dataset_name)
