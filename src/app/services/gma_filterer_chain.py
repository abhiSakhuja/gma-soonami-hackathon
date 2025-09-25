## Render conversation
"""
In this file we define a client that uses the LCEL (LangChain Expression Language)
methodology to define a conversation pipeline. In this way, the method is more customizable,
allowing to evaluate and trace each component separately.
"""
from typing import TypedDict, List, Optional
from langid.langid import LanguageIdentifier, model
from langchain_core.runnables import RunnableLambda, RunnableBranch, RunnablePassthrough
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

## Initialize it here, so it does not take time in every execution
identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)



class State(TypedDict):
    question: str
    translated_query: Optional[str]
    cuisine_types_retrieved: Optional[List]
    business_types_retrieved: Optional[List]
    filters: Optional[dict]



class Assistant_Rag:
    """
    Class for managing RAG (Retrieval-Augmented Generation) system.
    """
    def __init__(
            self,
            filter_extraction_chain,
            cuisine_type_retriever,
            business_type_retriever,
            translation_chain,
            opik_tracer,
            logger=None
        ) -> None:

        """
        Initialize the RAG system with retriever and LLM
        """
        # Initialize all resources:
        # self.db = initializer.get_vector_db()
        ## Neccessary processes:
        self.translation_chain = translation_chain
        self.filter_extraction_chain = filter_extraction_chain
        self.cuisine_type_retriever = cuisine_type_retriever
        self.business_type_retriever = business_type_retriever
        self.opik_tracer = opik_tracer
        process = StateGraph(State)
        # --- Define Nodes ---
        process.add_node("translate", self.translate)
        process.add_node("retrieve_cuisine", self.query_cuisine_index)
        process.add_node("retrieve_business_types", self.query_business_types_index)
        process.add_node("extract_filter", self.extract_filters)


        # Conditional transition from validate_language
        process.set_conditional_entry_point(
            self.validate_language,
            {
                True: "translate",
                False: "retrieve_cuisine"

                
            }
        )

        ## Define the edges
        process.add_edge("translate", "retrieve_cuisine")
        process.add_edge("retrieve_cuisine", "retrieve_business_types")
        process.add_edge("retrieve_business_types", "extract_filter")

        # End after filter extraction
        process.add_edge("extract_filter", END)

        graph = process.compile()

        self.graph = graph.with_config({
                        "callbacks": [self.opik_tracer]
                    })


    def translate(self, state):
        """Translates the original question

        Args:
            state (_type_): _description_
        """
        translation = self.translation_chain.invoke(state['question'])

        return {'translated_query': translation}

    def validate_language(self, state):
        """Validates the original language of the query

        Args:
            state (_type_): _description_

        Returns:
            _type_: _description_
        """
        print("GOing to validate the language of", state['question'])
        language, confidence = identifier.classify(state['question'])
        print("Language", language)
        print("Confidence --->", confidence)
        return language != "en" and confidence >= 0.7


    

    def query_cuisine_index(self, state):
        """Query cuisine types index to get relevant cuisine suggestions

        Args:
            state: Current state with question/translated_query

        Returns:
            dict: State update with cuisine_types_retrieved
        """
        question = state.get("translated_query") or state["question"]
        print("Retrieving cuisines for --->", question)
        return {'cuisine_types_retrieved': self.cuisine_type_retriever.query_index(query_str = question)}
    
    def query_business_types_index(self, state):
        """Query business types index to get relevant business type suggestions

        Args:
            state: Current state with question/translated_query

        Returns:
            dict: State update with business_types_retrieved
        """
        question = state.get("translated_query") or state["question"]
        print("Retrieving business types for --->", question)
        return {'business_types_retrieved': self.business_type_retriever.query_index(query_str = question)}
    
    def extract_filters(self, state):
        """Extract filters using the question and retrieved context

        Args:
            state: Current state with question, cuisine types, and business types
        """
        question = state.get("translated_query") or state["question"]
        cuisine_types = state.get("cuisine_types_retrieved", [])
        business_types = state.get("business_types_retrieved", [])
        
        # Build context for the LLM
        context = {
            'question': question,
            'available_cuisines': cuisine_types,
            'available_business_types': business_types
        }
        
        retrieved_filters = self.filter_extraction_chain.invoke(context)

        return {'filters': retrieved_filters}


    # def route(self,entities):
    #     if entities['search_type']=="Inside" and entities['Place']:
    #         print("Invoking with value--->",entities['Place'])
    #         entities['polygon'] = self.location_retriever.invoke(entities['Place'])
    #     return entities
