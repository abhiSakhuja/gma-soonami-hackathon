
import os
import yaml

import os
import logging
import logging.config

from langchain_groq import ChatGroq
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate

from src.app.utils.common.config_loader import ConfigLoader
from src.app.utils.aws.secrets_manager_client import SecretsManagerClient
from src.app.services.gma_filterer_chain import Assistant_Rag
from src.app.services.reranker_chain import RerankingChain
from src.app.services.llm_components import StructuredOutputChainComponent
from src.app.services.filterer import Filterer

## Import the schema
from src.app.schemas import filters_schema, translation_schema, reranker_schema
from src.app.monitoring.opik_utils import configure_opik
from src.app.utils.aws.s3_cli import S3Service
from opik.integrations.langchain import OpikTracer



class ResourceInitializer:
    def __init__(self) -> None:
        self.environment = os.getenv("env")
        self.platform = os.getenv("platform")
        self.config = ConfigLoader(env=self.environment).config
        self.aws_region = self.config.get("AWS_REGION")
        self.secrets_manager_client = SecretsManagerClient(region_name=self.aws_region)
        self.logger = self._set_up_logger()
        configure_opik(api_key = self.secrets_manager_client.get_secret(
                self.config.get("OPIK_SECRET"))["api_key"],
                project="GMA"
            )

    def _set_up_logger(self):
        logger_name = self.config.get("LOGGER_NAME")
        logging.config.dictConfig(self.config.get("LOGGING_CONFIG"))
        return logging.getLogger(logger_name)

    def get_s3_client(self):
        self.logger.info("Getting S3")

        return S3Service()

    # def _get_llm(self,  system_config) -> ChatGroq:
    #     """
    #     Initializes the LLM with the provided API key and configuration.

    #     :param api_key: The API key for the LLM.
    #     :return: An instance of the ChatGroq model.
    #     """
    #     llm = ChatGroq(
    #         model=system_config.get("model_name"),
    #         groq_api_key=self.secrets_manager_client.get_secret(self.config.get("GROQ_SECRET"))["api_key"],
    #         temperature=0 # TODO: do not hardcode this
    #     )
    #     return llm

    def _get_llm(self):
        """
        Initializes the LLM with the provided API key and configuration.

        :param api_key: The API key for the LLM.
        :return: An instance of the LLM model (ChatGroq or AzureChatOpenAI).
        :raises ValueError: If required configuration is missing or platform is unsupported.
        """

        self.logger.info("Getting Review Aggregator...")
        if self.platform.upper() == "AZURE":
            llm_api_key = self.secrets_manager_client.get_secret(self.config.get("AZURE", {}).get("OPENAI_API_SECRET"))["api_key"]
        elif self.platform.upper() == "GROQ":
            llm_api_key = self.secrets_manager_client.get_secret(self.config.get("GROQ_SECRET"))["api_key"]
        else:
            raise ValueError(f"Unsupported platform: {self.platform}. Supported platforms are 'AZURE' and 'GROQ'.")

        if self.platform == "azure":
            self.logger.info("Using Azure OpenAI model...")
            if not self.config.get("AZURE", {}).get("OPENAI_ENDPOINT", ""):
                raise ValueError("Azure base URL must be provided for Azure OpenAI model.")
            llm = AzureChatOpenAI(
                azure_endpoint=self.config.get("AZURE", {}).get("OPENAI_ENDPOINT", ""),
                azure_deployment=self.config.get("AZURE", {}).get("OPENAI_DEPLOYMENT_NAME", ""),
                api_version=self.config.get("AZURE", {}).get("OPENAI_API_VERSION", ""),
                api_key=llm_api_key,
                temperature=0.3 ## TODO: do not hardcode this
            )
            return llm
        elif self.platform == "groq":
            self.logger.info("Using Groq model...")
            if not self.groq_model_name:
                raise ValueError("Groq model name must be provided for Groq model.")
            llm = ChatGroq(
                model=self.config.get("GROQ_MODEL_NAME"),
                groq_api_key=llm_api_key,
                temperature=0.3 ## TODO: do not hardcode this   
            )
            return llm
        else:
            self.logger.error(f"Unsupported LLM platform: {self.platform}")
            raise ValueError(f"Unsupported LLM platform: {self.platform}")
    
    def __get_cuisine_type_filterer(self):
        vector_db_config = {
            'index_name':self.config.get("PINECONE_DB").get("INDEX_NAME"),
            "namespace": "", # TODO: Add to config
            'api_key':self.secrets_manager_client.get_secret(
                 self.config.get("PINECONE_DB").get("SECRET")
                ).get("api_key"),
            'server_url': self.config.get("EC2").get("PRIVATE_IP"),
            'aws_region':self.config.get("AWS_REGION"),
            "port": self.config.get("EC2").get("PORT"),
            'logger':self.logger
            }
        return Filterer(config = vector_db_config)
    
    def __get_business_type_filterer(self):
        vector_db_config = {
            'index_name': "business-types-index",  # New index for business types
            "namespace": "", # TODO: Add to config
            'api_key':self.secrets_manager_client.get_secret(
                 self.config.get("PINECONE_DB").get("SECRET")
                ).get("api_key"),
            'server_url': self.config.get("EC2").get("PRIVATE_IP"),
            'aws_region':self.config.get("AWS_REGION"),
            "port": self.config.get("EC2").get("PORT"),
            'logger':self.logger
            }
        return Filterer(config = vector_db_config)


    def get_filterer_agent(self, system_config):
        logging.info(f"Going to load model---> {system_config.get('filter_pipeline').get('model_name')}")


        llm = self._get_llm()
        opik_tracer = OpikTracer(tags=["EntityExtraction"])
        cuisine_retriever = self.__get_cuisine_type_filterer()
        business_type_retriever = self.__get_business_type_filterer()
        ## Define the Subcomponents of the final chain:
        filter_template = system_config.get('filter_pipeline').get("prompt")
        translate_prompt = system_config.get('filter_pipeline').get("translate_prompt")

        filter_prompt = ChatPromptTemplate.from_template(filter_template)
        translate_prompt =ChatPromptTemplate.from_template(translate_prompt)

        filter_extraction_chain = StructuredOutputChainComponent(filter_prompt, llm, filters_schema).build_chain()
        translation_chain = StructuredOutputChainComponent(translate_prompt, llm, translation_schema).build_chain()

        return Assistant_Rag(
            filter_extraction_chain= filter_extraction_chain,
            cuisine_type_retriever= cuisine_retriever,
            business_type_retriever= business_type_retriever,
            translation_chain= translation_chain,
            opik_tracer=opik_tracer
        )
    

    def get_reranker(self, system_config):
        logging.info(f"Going to load reranker with model---> {system_config.get('filter_pipeline').get('model_name')}")
        reranker_template = system_config.get('filter_pipeline').get("reranking_prompt")

        llm = self._get_llm()
        opik_tracer = OpikTracer(tags=["Reranker"])
        reranker_prompt = ChatPromptTemplate.from_template(reranker_template)

        llm = llm.with_structured_output(
            reranker_schema,
            method = "json_mode"
            )

        return RerankingChain(
            scoring_prompt = reranker_prompt,
            llm = llm,
            opik_tracer=opik_tracer
        )
