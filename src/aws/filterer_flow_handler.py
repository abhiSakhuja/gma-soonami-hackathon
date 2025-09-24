import asyncio

from pydantic import ValidationError
from src.app.schemas.data_models import *  # Assuming you placed your models in src/app/models.py
from src.app.services.business_formatter import format_business_metadata
from src.app.utils.common.utils import merge_dicts_by_id, filter_dicts
from src.app.resource_initializer import ResourceInitializer
from src.app.services.filter_service import FilterService
import requests
import os
import json
import yaml
from pathlib import Path
from src.app.services.business_formatter import format_business_metadata
from src.app.utils.common.time_decor import timeit, timeblock


# Get the current file's directory
current_file_path = Path(__file__).resolve()  # Path to the current file
current_dir = current_file_path.parent.parent      # Directory containing the current file

# Construct the full path to the config file
config_path = current_dir / "app" / "config" / "pipeline_config.yaml"

# API Gateway endpoint URL (replace with your actual URL)

## Load config
with open(config_path, "r", encoding='utf-8') as file:
    chain_config = yaml.safe_load(file)
## Create connections to the SDKs outside the main function:
resource_initializer = ResourceInitializer()

## TODO: Rename
reranker_client =resource_initializer.get_reranker(chain_config)
agent = resource_initializer.get_filterer_agent(chain_config)

s3_client = resource_initializer.get_s3_client()
logger = resource_initializer.logger
config = resource_initializer.config

PINECONE_URL = config.get("PINECONE_URL")
API_URL = config.get("API_URL")

# Filter mapping and service
filter_mapping = {
    "cuisine_type": "processed_refined_cuisine_types_001",  # Keep both for compatibility
    "business_type": "processed_refined_business_types_001",  # Keep both for compatibility
    "processed_overall_score_001": "processed_avg_score_001", ## TODO: Change this field in the extraction already
}

filter_service = FilterService(default_mapping=filter_mapping)

def parse_event(event: dict) -> FilterEvent:
    try:
        return FilterEvent.model_validate(event)
    except ValidationError as e:
        logger.error(f"Invalid input: {e}")
        raise

@timeit("get_filters", logger)
def get_filters(input_query: str, filter_type: Optional[str], city_code: Optional[str],country_code: Optional[str] = "es" ) -> (dict, dict):
    filter_state = agent.graph.invoke({"question": input_query})
    filters = filter_state['filters']
    logger.info(f"Retrieved filters: {filter_state['filters']}")

    if filter_type:
        params = {"filter_type": filter_type.lower()}
        if filter_type.lower() == "city":
            params["city_code"] = city_code
            params['country_code'] = country_code
    else:
        params = {"filter_type": filters.get("search_type", "around").lower()}

    return filters, params, filter_state


@timeit("call_filter_service", logger)
def call_filter_service(body: dict, params: dict) -> list:
    logger.info(f"Calling filter service with filters: {body} {params}")
    response = requests.post(API_URL, data=json.dumps(body), params=params)
    data = response.json()
    return data.get("body", [])

@timeit("call_pinecone", logger)
def call_pinecone(ids: list, query: str, city: str = "vlc") -> list:
    payload = {"business_IDS": ids, "query": query}
    response = requests.post(PINECONE_URL, data=json.dumps(payload), params={"city": city}, timeout=100)
    return response.json().get("body", {}).get("matches", [])

@timeit("Rerank", logger)
def rerank_businesses(businesses: list, query: str) -> list:
    logger.info(f"Starting reranking for {len(businesses)} businesses")
    formatted = [format_business_metadata(b.get("metadata")) for b in businesses]
    logger.info(f"Formatted {len(formatted)} businesses for reranking")
    
    # reranker_chain = reranker_client.set_rag_pipeline(formatted)
    # result = reranker_chain.invoke({"input": query},config={"callbacks": [reranker_client.opik_tracer]})

    # reranker_client is what get_reranker(...) now returns (RerankingGraph)
    logger.info("Building reranker graph...")
    graph = reranker_client.build()

    

# Invoke with asyncio so fan-out runs concurrently
# initial_state = {"input": ..., "business": [...]}  # your data
# result = await graph.ainvoke(initial_state)
    logger.info("Invoking reranker graph with OpikTracer...")
    result = asyncio.run(
        graph.ainvoke(
            {"input": query, "business": formatted},
            config={"callbacks": [reranker_client.opik_tracer]},
        )
    )
    logger.info(f"Reranker result: {result.keys() if result else 'None'}")

    scores_by_id = {item['business_id']: {'score': item['score'], 'reason': item['reason']}
                    for item in result.get("sorted_businesses", [])}

    # Update original businesses with scores and reasons
    updated_businesses = []
    for biz in businesses:
        biz_id = biz.get("metadata", {}).get("business_id")
        if biz_id in scores_by_id:
            biz.update(scores_by_id[biz_id])
            updated_businesses.append(biz)

    # Sort businesses based on score
    updated_businesses.sort(key=lambda x: x['score'], reverse=True)

    return updated_businesses


@timeit("Split by Score", logger)
def split_by_score(data: list, n: int):
    """
    Splits a list of dictionaries into two lists based on a score threshold.
    The first n items go into one list, and the rest into another.
    
    Args:
        data (list): List of dictionaries, each containing a 'score' field.
        threshold (float): The score threshold to split the lists.
    
    Returns:
        tuple: (top_n, remaining)
        - top_n: First n dictionaries sorted by score in descending order.
        - remaining: The rest of the dictionaries.
    """
    print("Trying to split business")
    # Sort data by score in descending order
    sorted_data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)

    # Split into two lists
    top_n = sorted_data[:n]
    remaining = sorted_data[n:]

    return top_n, remaining

@timeit("get_data", logger)
def get_data(s3_client, places: List, country_code: str = "es", city_code: str = "vlc"):
    """
    Retrieve from S3 the metadata for the business
    """

    for place in places:
        business_id = place.get("id")
        date_range = place.get("processed_daterange_001")
        language = "en"
        # Construct the S3 key
        s3_key = f'prc/geo/{country_code}/{city_code}/{business_id}/summary/001_{date_range}_{language}.json'

        summary_json = s3_client.load_json_as_dict(bucket_name="gma-dev-data-364969088603-eu-central-1-s3", key=s3_key)

        place['metadata'] = summary_json

    return places


def data_filterer_handler(event, context):
    """
    Handler that handles the input event
    for the filtering microservice

    Args:
        event (_type_): _description_
        context (_type_): _description_

    Returns:
        _type_: _description_
    """
    logger.info("Event----> %s", str(event))
    event_data = parse_event(event)
    query = event_data.filter_data.natural_query
    filters, params, full_state = get_filters(query, event_data.filter_type, event_data.city_code,  event_data.country_code)
    logger.info("Extracted filters ---> %s", str(filters))
    logger.info("Extracted filter keys ---> %s", list(filters.keys()))
    
    # Process extracted filters (transform values and apply mapping)
    processed_filters = filter_service.process_extracted_filters(filters, filter_mapping)
    logger.info("Processed extracted filters ---> %s", str(processed_filters))
    
    # Merge with existing filters
    existing_filters = event_data.filter_data.filters
    merged_filters = filter_service.merge_filters(existing_filters, processed_filters)
    logger.info("Final merged filters ---> %s", str(merged_filters))
    
    # Clean empty dictionaries to None to prevent filter endpoint failures
    cleaned_filters = filter_service.clean_empty_filters(merged_filters)
    logger.info("Cleaned filters (empty {} -> None) ---> %s", str(cleaned_filters))

    body = event_data.filter_data.model_dump()
    body["filters"] = cleaned_filters

    results = call_filter_service(body, params)
    if not results:
        logger.info("Not results Retrieved from DynamoDB")
        return {
            "statusCode":200,
            "body":str(filters),
            "recommended_result":[],
            "rest_result":[]
        }

    ids = [item["id"] for item in results]
    query = full_state.get("translation", query)
    pinecone_matches = call_pinecone(ids, query)

    results = merge_dicts_by_id(results, pinecone_matches, "id")


    top_n = 30
    recommended, rest = split_by_score(results, top_n)
    

    recommended = get_data(s3_client=s3_client, places = recommended)

    if event_data.filter_data.global_fields:
        if "id" not in event_data.filter_data.global_fields:
            event_data.filter_data.global_fields.append("id")
        if "metadata" not in event_data.filter_data.global_fields:
            event_data.filter_data.global_fields.append("metadata")

        recommended = filter_dicts(recommended, event_data.filter_data.global_fields)
        rest = filter_dicts(rest, event_data.filter_data.global_fields)

    try:
        recommended = rerank_businesses(recommended, query)
        logger.info("Places succesfully sorted")

    except Exception as e:
        logger.error(f"Reranking failed: {e}")

    return {
        "statusCode":200,
        "body":str(filters),
        "recommended_result":recommended,
        "rest_result":rest
    }
