from logging import Logger
from typing import Dict, Any, List, Tuple

from pinecone import Pinecone, ServerlessSpec

from src.app.services.sentence_transformers_embeddings import SentenceTransformerAPIEmbeddings


class VectorDBClient():
    def __init__(
        self,
        index_name: str,
        namespace: str,
        api_key: str,
        server_url: str,
        aws_region: str,
        port: str,
        logger: Logger
        ) -> None:
        self.logger = logger
        self.client = Pinecone(api_key=api_key)
        self.logger.info(f"Initializing index--->{index_name}")
        self.index = self.client.Index(name=index_name)
        self.index_name = index_name
        self.namespace = namespace
        self.embedding_model = SentenceTransformerAPIEmbeddings(server_url=server_url,port = port, logger=self.logger)
        self.aws_region = aws_region
        
        
    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to the Pinecone index instance.
        """
        return getattr(self.index, name)
        
    def create_index(self, index_name: str, dimension: int, metric: str="cosine") -> None:
        """
        Creates a new index in the Pinecone vector database if it does not already exist.

        :param index_name: The name of the index to create.
        :param dimension: The dimensionality of the vectors that will be stored in the index.
        :param metric: The distance metric to use for the index. Default is "cosine".
        :return: None
        """
        self.logger.debug(f"Creating index {index_name} with {dimension} dimensions, and metric {metric}...")
        pc_index_names = [idx["name"] for idx in self.client.list_indexes()]
        if index_name not in pc_index_names:
            self.client.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                cloud="aws",
                region=self.aws_region
                )
            )
            self.logger.info(f"Index {index_name} created succesfully.")
        else:
            self.logger.info(f"Index {index_name} already exists.")


    def upsert_record(self, doc_id:str, doc_text:str, doc_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upserts a document record into the index, creating or updating it as needed.

        :param doc_id: The unique identifier for the document to be upserted.
        :param doc_text: The content of the document as a string, which will be processed into embeddings.
        :param doc_metadata: Metadata associated with the document, provided as a dictionary.
        :return: A dictionary containing the upsert operation response, including the number of records upserted, for example: {'upserted_count': 1}.
        """
        self.logger.debug(f"Upserting record into index {self.index_name} in namespace {self.namespace}...")
        doc_embedding = self.embedding_model.embed_documents(doc_text)
        doc = tuple([doc_id, doc_embedding, doc_metadata])
        response = self.index.upsert(vectors=[doc], namespace=self.namespace)
        self.logger.info(f"Index upsert response {response}.")
        return response
