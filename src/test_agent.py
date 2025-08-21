from langgraph_sdk import get_client

client = get_client(url="http://127.0.0.1:2024")

async def test_sql_agent():
    config = {
        "configurable": {"domain": "postgres"},
        "user_id": "2",
    }
        
    async for chunk in client.runs.stream(
        None,  
        "sql_agent", 
        input={
            "counter": 0,
            "input": "Empleado mas antiguo"
        },
        config=config
    ):
        print(f"Receiving new event of type: {chunk.event}...")
        print(chunk.data)
        print("\n\n")

async def test_rag_agent():
    user_email = "test_user@snoopconsulting.com"
    provider = "pinecone"  # The vector store provider
    index_name = "edwards-sgc-testing"  # The name of the vector store index
    storage_service_type = "drive"


    config = {
        "configurable": {"domain": "postgres"},
        "user_email": user_email,
        "provider": provider,
        "index_name": index_name,
        "storage_service_type": storage_service_type,
    }
        
    input = {
            "messages": ["Que es un hallazgo?"],
            "retry_count_grade_documents": 1,
            "retry_count_hallucinations": 3,
            "error": False,
            "reflection": False,
            "current_user": "test_user@snoopconsulting.com"
        }

    async for chunk in client.runs.stream(
        None,  
        "reflexive_rag_agent", 
        input=input,
        config=config
    ):
        print(f"Receiving new event of type: {chunk.event}...")
        print(chunk.data)
        print("\n\n")
        

async def test_transaction_agent():
       
    async for chunk in client.runs.stream(
        None,  
        "transaction_agent", 
        input={
            "messages": ["Quiero cargar un hallazgo"],
        },
    ):
        print(f"Receiving new event of type: {chunk.event}...")
        print(chunk.data)
        print("\n\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rag_agent())
    #asyncio.run(test_sql_agent())
    #asyncio.run(test_transaction_agent())