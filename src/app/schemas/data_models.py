from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class BusinessMetadata(BaseModel):
    business_id: str
    business_summary: str
    business_type: Optional[str] = None
    cuisine_type: Optional[List[str]] = []
    price_range: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    food_score: Optional[float] = None
    service_score: Optional[float] = None
    atmosphere_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    must_try: Optional[List[str]] = []
    must_avoid: Optional[List[str]] = []
    positive_aspects: Optional[List[str]] = []
    negative_aspects: Optional[List[str]] = []

class Business(BaseModel):
    id: str
    name: Optional[str]
    metadata: BusinessMetadata



## Input for lambda event
class Coordinates(BaseModel):
    lat: float
    lng: float


class FilterData(BaseModel):
    natural_query: Optional[str] = None
    filters: Optional[Dict] = {}
    global_fields: Optional[List[str]] = None
    location: Optional[Coordinates] = None
    radius: Optional[int] = None


class FilterEvent(BaseModel):
    filter_data: FilterData
    filter_type: Optional[str] = None
    city_code: Optional[str] = None


# ## Lambda response
# class FiltererResponse(BaseModel):
#     statusCode: int
#     body: str
#     recommended_results: List[Business]
#     rest_results: Optional[List[Business]] = []
