import os
import requests
import logging
from typing import List
from langchain.embeddings.base import Embeddings  # or wherever Embeddings is imported from

class SentenceTransformerAPIEmbeddings(Embeddings):
    def __init__(self, server_url: str = None, port: str = None, logger=None):
        """
        :param server_url: Base URL of the FastAPI server, e.g. http://localhost:8000
        :param logger: optional logger object
        """
        self.logger = logger if logger else logging.getLogger(__name__)
        self.server_url = "http://" + server_url + ':' + port

        if not self.server_url:
            raise ValueError("No server_url provided and EMBEDDING_API_URL env var is not set.")

        # Optionally verify you can reach the server
        self.logger.info(f"Initializing SentenceTransformerAPIEmbeddings with URL: {self.server_url}")

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Calls the remote FastAPI endpoint to embed multiple documents,
        replicating the same signature and return type as the local method.
        """
        endpoint = f"{self.server_url}/embed_documents"

        self.logger.debug(f"Sending {len(documents)} documents to {endpoint}...")
        
        # Construct the request data per your FastAPI schema
        data = {"documents": documents}

        response = requests.post(endpoint, json=data)
        response.raise_for_status()  # raise an exception if the call failed

        # The response is expected to have the structure: {"embeddings": [[...], [...]]}
        result_json = response.json()
        return result_json["embeddings"]

    def embed_query(self, query: str) -> List[float]:
        """
        Calls the remote FastAPI endpoint to embed a single query,
        replicating the same signature and return type as the local method.
        """
        endpoint = f"{self.server_url}/embed"

        self.logger.debug(f"Sending query '{query}' to {endpoint}...")
        
        params = {"query": query}
        
        response = requests.get(endpoint, params=params)
        response.raise_for_status()

        self.logger.info(f"Endpoint response: {response.content}")

        result_json = response.json()

        self.logger.info(f"Returning response")
        
        return result_json["embed"]

