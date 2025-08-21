from dotenv import load_dotenv
from langsmith import Client
import os, requests
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage
from simple_llm_with_tools import invoke
from models.chat_models import models

load_dotenv()

LANGCHAIN_END = os.getenv('LANGCHAIN_END')
LANGCHAIN_API = os.getenv('LANGCHAIN_API')
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv('AZURE_OPENAI_CHATGPT_DEPLOYMENT')
langchain_client = Client(api_url=LANGCHAIN_END, api_key=LANGCHAIN_API)



class Grade(BaseModel):
  score: bool = Field(
      description="Boolean that indicates whether the response is accurate relative to the reference answer"
  )


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

        
def accuracy(outputs: dict, reference_outputs: dict) -> bool:

    instructions = """Evaluate Student Answer against Ground Truth for conceptual similarity and classify true or false: 
    - False: No conceptual match and similarity
    - True: Most or full conceptual match and similarity
    - Key criteria: Concept should match, not exact wording.
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


def target(inputs: dict) -> dict:

    try:
        response, _ = invoke(inputs["Pregunta"])
        assistant_response = response.content
    except requests.exceptions.RequestException as e:
        assistant_response = "Hubo un error al obtener respuesta del bot."
    return { 
        "response": assistant_response
    }


def evaluate(dataset_name, metric):

    print("Evaluando...")

    examples = list(langchain_client.list_examples(dataset_name=dataset_name))
    examples.sort(key=lambda example: example.inputs["ID"], reverse=False)

    langchain_client.evaluate(
        target,
        data=examples,
        evaluators=[
            metric,
        ],
        experiment_prefix="llm_rag_evaluation",
        max_concurrency=10,
        num_repetitions=10
    )


csv_path = 'test_cases'
dataset_name = "llm_edwards_test_cases_rag"
csv_file = 'rag_test_cases.csv'
create_dataset(dataset_name, csv_path, csv_file)
evaluate(dataset_name, accuracy)