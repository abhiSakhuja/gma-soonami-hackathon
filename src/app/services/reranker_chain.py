## Render conversation
"""
In this file we define a client that uses the LCEL (LangChain Expression Language)
methodology to define a conversation pipeline. In this way, the method is more customizable,
allowing to evaluate and trace each component separately.
"""
from langchain_core.runnables import RunnableLambda, RunnableBranch, RunnablePassthrough




class RerankingChain:
    """
    Class for managing RAG (Retrieval-Augmented Generation) system.
    """
    def __init__(
            self,
            scoring_prompt,
            llm,
            opik_tracer,
            logger=None
        ) -> None:

        """
        Initialize the RAG system with retriever and LLM
        """
        # Initialize all resources:
        # self.db = initializer.get_vector_db()

        self.opik_tracer = opik_tracer
        self.scoring_prompt = scoring_prompt
        self.llm = llm



    def merge_results(self):
        def _merge(results_dict):
            all_results = []
            for group_result in results_dict.values():
                all_results.extend(group_result["business_scores"])
            # Sort businesses by score in descending order
            sorted_businesses = sorted(all_results, key=lambda x: x["score"], reverse=True)
            return {"sorted_businesses": sorted_businesses}
        return RunnableLambda(_merge)


    def set_rag_pipeline(self, business):
        """_summary_
        """
        # Split the list into chunks of 5
        chunks = [business[i:i + 5] for i in range(0, len(business), 5)]
        parallel_chains = {
            f"group_{i}": self.scoring_prompt.partial(business=chunk) | self.llm
            for i, chunk in enumerate(chunks)
        }

        main_chain = parallel_chains | self.merge_results()

        return main_chain.with_config(
            {"callbacks": [self.opik_tracer]}
        )
