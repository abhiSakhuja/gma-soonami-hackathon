from src.app.services.vector_db_client import VectorDBClient


from typing import Any, Dict, List
from datetime import datetime



class Filterer(VectorDBClient):
    def __init__(
        self,
        config: dict
        ) -> None:
        super().__init__(**config)


    def retrieve_by_ids(self, ids:list )-> list:
        """Function to retrieve a set of Records only based
        on their ID's

        Args:
            ids (List): List of IDs to retrieve
        """
        self.logger.debug(f"Retrieving records from index {self.index_name} in namespace {self.namespace}...")
        business = self.index.fetch(ids=ids, namespace=self.namespace)

        return business

    def query_index(self, query_str:str, metadata: dict = {})-> list:
        """Function to query an index by both metadata and Text based 

        Args:
            query_str (str): Query to be used to filter the index
            metadata(dict): All kind of filters wanted to be performed

        Returns:
            list: Results with all information from the Index
        """
        doc_embedding = self.embedding_model.embed_query(query_str)
        business_ids = metadata.get("business_id", {}).get("$in", [])

        k = len(business_ids) if business_ids else 20
        self.logger.info(f"Filtering index with data--->{doc_embedding[:5]} and filters--->{metadata}")

        query_params = {
            "vector": doc_embedding,
            "include_metadata": True,
            "top_k": k,
            "namespace":self.namespace
        }

        # Conditionally include the filter if metadata is not empty
        if metadata:
            query_params["filter"] = metadata

        # Call the query with unpacked parameters
        response = self.index.query(**query_params)
        return response
