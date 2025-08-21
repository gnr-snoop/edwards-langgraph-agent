import os

os.environ["AZURESEARCH_FIELDS_CONTENT_VECTOR"] = "embedding"

from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings

from rag_agent.document import Document
from rag_agent.vector_stores.vector_search_service import VectorSearch


class AzureVectorSearch(VectorSearch):

    def __init__(self, api_key, endpoint, index_name, embedding_model: AzureOpenAIEmbeddings):
        
        self._vector_store = AzureSearch(
            azure_search_key=api_key,
            embedding_function=embedding_model.embed_query,
            index_name=index_name,
            azure_search_endpoint=endpoint,
            semantic_configuration_name="default",
        )

    def get_vector_store(self):
        return self._vector_store
    
    async def retrieve(self, question):
       
        response = await self._vector_store.asimilarity_search(question, k=5)
        
        container_path = "https://st7u7cm3u3wwcww.blob.core.windows.net/content/"
        documents = []
        
        for doc in response:
            title = doc.metadata['sourcefile']
            text = doc.page_content
            link = container_path + title
            new_document = Document(text, title, link)
            documents.append(new_document)
        
        return documents
