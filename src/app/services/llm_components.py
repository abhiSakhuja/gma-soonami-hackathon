import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from langchain.prompts import ChatPromptTemplate
from langchain.schema.agent import AgentFinish
from langchain.schema.runnable import Runnable
from langchain_groq import ChatGroq



# =============================================================================
# Abstract Base Chain Component
# =============================================================================
class BaseChainComponent(ABC):
    """
    Abstract base class for all chain components.
    Ensures all subclasses implement `build_chain()` and return a valid LangChain `Runnable`.
    """

    def __init__(self, prompt: ChatPromptTemplate, llm: ChatGroq) -> None:
        self.prompt = prompt
        self.llm = llm

    @abstractmethod
    def build_chain(self) -> Runnable:
        """Abstract method that must be implemented by subclasses to return a `Runnable`."""


# =============================================================================
# Simple LLM Chain (Only Prompt + LLM, No Tools)
# =============================================================================
class SimpleLLMChain(BaseChainComponent):
    """
    A basic LLM chain that only consists of a prompt and an LLM.
    It does NOT involve tools or structured output enforcement.
    """

    def build_chain(self) -> Runnable:
        """Return a simple `Runnable` chain: Prompt → LLM."""
        return self.prompt | self.llm



# =============================================================================
# Component that Enforces Structured Output Using a JSON Schema
# =============================================================================
class StructuredOutputChainComponent(BaseChainComponent):
    """
    This component ensures that the output follows a structured JSON schema.
    """

    def __init__(
        self, prompt: ChatPromptTemplate, llm: ChatGroq, json_schema: dict
    ) -> None:
        self.json_schema = json_schema
        super().__init__(prompt, llm)

    def build_chain(self) -> Runnable:
        """Modify the LLM to return structured output and return a `Runnable`."""
        structured_llm = self.llm.with_structured_output(
            self.json_schema,
            method = "json_mode"
        ) 
        return self.prompt | structured_llm