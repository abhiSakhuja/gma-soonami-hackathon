# schema.py
filters_schema = {
    "title": "Business Search Query",
    "description": "Structured search request for the travel assistant chatbot.",
    "type": "object",
    "properties": {
        "search_type": {
            "type": "string",
            "enum": ["Around", "Inside", "Near to"],
            "description": "Type of search to be applied",
            "default": "Around"
        },
        "place": {
            "type": "string",
            "default": "",
            "description": "Place where the search wants to be performed"
        },
                "business_type": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["Restaurant"],
            "description": "Types of business to be searched (e.g., Restaurant, Cafe, Bakery, Fine Dining)"
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Relevant keywords for the search"
        },
        "min_price": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1000,
            "description": "Minimum price per person in euros"
        },
        "max_price": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1000,
            "description": "Maximum price per person in euros"
        },
        "cuisine_type": {
            "type": "array",
            "default": [],
            "description": "Type of cuisine (e.g., Italian, Sushi, Vegan), can have multiple types"
        },
        "overall_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 5.0,
            "description": "Overall score of the business"
        },
        "atmosphere_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 5.0,
            "description": "Atmosphere score of the business"
        },
        "food_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 5.0,
            "description": "Food score of the business"
        },
        "sentiment_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 5.0,
            "description": "Sentiment score of the business"
        },
        "service_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 5.0,
            "description": "Service score of the business"
        }
    },
    "required": ["search_type", "business_type", "keywords"]
}


## Translation json schema
translation_schema = {
    "title": "TranslationSchema",
    "type": "object",
    "properties": {
        "translation": {
            "type": "string",
            "description": "The translated version of the input text"
        }
    },
    "required": ["translation"]
}


reranker_schema = {
  "title": "BusinessScores",
  "type": "object",
  "properties": {
    "business_scores": {
      "type": "array",
      "description": "A list of businesses with their corresponding relevance scores.",
      "items": {
        "type": "object",
        "properties": {
          "business_id": {
            "type": "string",
            "description": "A unique identifier for the business."
          },
          "score": {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "description": "A float score from 0 to 10 indicating the relevance of the business to the user query."
          }
        },
        "required": ["business_id", "score"]
      },
      "minItems": 1
    }
  },
  "required": ["business_scores"]
}
