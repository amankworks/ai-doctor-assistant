import sys
from langchain_neo4j import Neo4jGraph
from my_doctor_assistant.utils.helper import get_neo4j_credentials

class Neo4jDBConnection:
    def __init__(self) -> None:
        self.connection = None

    def _build(self):
        try:
            # print("Trying to connect to Neo4j...")
            print("Trying to connect to Neo4j...", file=sys.stderr)
            uri, user, password = get_neo4j_credentials()
            self.connection = Neo4jGraph(
                url=uri,
                username=user,
                password=password,
                # enhanced_schema=True,
            )
            # print("Connected to Neo4j successfully.")
            print("Connected to Neo4j successfully.", file=sys.stderr)
        except Exception as e:
            # print(f"Error connecting to Neo4j: {e}")
            print(f"Error connecting to Neo4j: {e}", file=sys.stderr)
            # Raise the original error to avoid masking the real cause
            raise

    def get_connection(self):
        if self.connection is None:
            raise Exception("No active Neo4j connection. Please call start() first.")
        return self.connection

    def start(self):
        if self.connection is None:
            self._build()
        return self.get_connection()