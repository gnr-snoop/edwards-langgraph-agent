import os
import asyncio

from pinecone import Pinecone as pi
from langchain_pinecone import PineconeVectorStore
from langchain_openai import AzureOpenAIEmbeddings
from rag_agent.vector_stores.vector_search_service import VectorSearch
from rag_agent.document import Document



class PineconeVectorSearch(VectorSearch):
   
    def __init__(self, index_name: str, embedding_model: AzureOpenAIEmbeddings):
        self.index_name = index_name
        self.embedding_model = embedding_model


    async def retrieve(self, question):
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variables must be set.")
        pc = pi(api_key=api_key)
        #index = await asyncio.to_thread(pc.Index(self.index_name))
        index = pc.Index(self.index_name)
        self._vector_store = PineconeVectorStore(
            index=index,
            embedding=self.embedding_model,
            text_key='content'
        )

        response = await self._vector_store.asimilarity_search(question)
        documents = []

        for doc in response:
            filename = doc.metadata['filename']
            content = doc.page_content
            source = doc.metadata['source']
            new_document = Document(content, filename, source)
            documents.append(new_document)

        return documents


