from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.inmemory import InMemoryVectorStore

from rag_agent.vector_stores.azure_vector_search import AzureVectorSearch
from rag_agent.vector_stores.pinecone_vector_search import PineconeVectorSearch

import os
class VectorSearchFactory:
    
    @staticmethod
    def create_vectorial_instance(provider: str, index_name, embedding_model: AzureOpenAIEmbeddings):
        if(provider == "azure_search_service"):
            api_key = os.getenv("AZURE_SEARCH_API_KEY")
            endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            if not api_key or not endpoint:
                raise ValueError("AZURE_SEARCH_API_KEY and AZURE_SEARCH_ENDPOINT environment variables must be set.")
            return AzureVectorSearch(
                api_key=api_key,
                endpoint=endpoint,
                index_name=index_name,
                embedding_model=embedding_model
            )
        elif(provider == "pinecone"):
            return PineconeVectorSearch(index_name=index_name, embedding_model=embedding_model)
        elif(provider == "in_memory"):
            return InMemoryVectorStore(embedding_model)
        else:
            raise ValueError(f"Unknown provider '{provider}'.")
                