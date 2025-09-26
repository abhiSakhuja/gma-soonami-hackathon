from src.app.schemas.data_models import *


def parse_event(event: dict) -> FilterEvent:
    try:
        return FilterEvent.model_validate(event)
    except ValidationError as e:
        logger.error(f"Invalid input: {e}")
        raise


def get_filters(input_query: str, filter_type: Optional[str], city_code: Optional[str]) -> (dict, dict):
    filters = agent.chain.invoke({"question": input_query})
    logger.info(f"Retrieved filters: {filters}")

    if filter_type:
        params = {"filter_type": filter_type.lower()}
        if filter_type.lower() == "city":
            params["city_code"] = city_code
    else:
        params = {"filter_type": filters.get("search_type", "around").lower()}

    return filters, params


def call_filter_service(body: dict, params: dict) -> list:
    response = requests.post(API_URL, data=json.dumps(body), params=params)
    data = response.json()
    return data.get("body", [])


def call_pinecone(ids: list, query: str, city: str = "vlc") -> list:
    payload = {"business_IDS": ids, "query": query}
    response = requests.post(PINECONE_URL, data=json.dumps(payload), params={"city": city}, timeout=100)
    return response.json().get("body", {}).get("matches", [])


def rerank_businesses(businesses: list, query: str) -> list:
    formatted = [format_business_metadata(b.get("metadata")) for b in businesses]
    reranker_chain = reranker_client.set_rag_pipeline(formatted)
    result = reranker_chain.invoke({"input": query})
    return result.get("sorted_business_ids", [])


def split_by_score(data: list, n: int):
    sorted_data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_data[:n], sorted_data[n:]
