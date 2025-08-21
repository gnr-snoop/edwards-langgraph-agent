import os

from urllib.parse import quote_plus
from sqlalchemy import create_engine

from langchain_community.utilities import SQLDatabase


_bigquery_engine = None
_postgres_engine = None

def get_bigquery_engine():
    global _bigquery_engine
    if _bigquery_engine is None:
        service_account_file_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        service_account_file_path = os.path.abspath(service_account_file_path)
        
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        dataset = os.getenv("BIGQUERY_DATASET")
        if not project_id or not dataset:
            raise ValueError("GOOGLE_CLOUD_PROJECT and BIGQUERY_DATASET environment variables must be set.")
        sqlalchemy_url = f'bigquery://{project_id}/{dataset}'
        _bigquery_engine = create_engine(
            sqlalchemy_url,
            credentials_path=service_account_file_path
        )
    return _bigquery_engine

def get_postgres_engine():
    global _postgres_engine
    if _postgres_engine is None:
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        dbname = os.getenv("POSTGRES_DB")
        if not user or not password or not host or not port or not dbname:
            raise ValueError("POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, and POSTGRES_DB environment variables must be set.")

        # Create the SQLAlchemy engine for PostgreSQL
        user_enc = quote_plus(user)
        password_enc = quote_plus(password)
        sqlalchemy_url = f'postgresql://{user_enc}:{password_enc}@{host}:{port}/{dbname}?gssencmode=disable'
        _postgres_engine = create_engine(sqlalchemy_url)
    return _postgres_engine

def get_sqlalchemy_engine(db_type):
    """
    Get the SQLAlchemy engine based on the configured database type.
    """
    if db_type == "bigquery":
        engine = get_bigquery_engine()
    elif db_type == "postgres":
        engine = get_postgres_engine()
    else:
        raise ValueError(f"Unsupported db_type: {db_type}")

    return SQLDatabase(engine)

engine = get_sqlalchemy_engine("bigquery")  # Default to PostgreSQL