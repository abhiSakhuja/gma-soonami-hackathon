from typing import Dict, Any, Optional, Union, List
from src.app.schemas.filter_models import Filters, FilterValue


class FilterService:
    """Service for handling filter operations"""
    
    def __init__(self, default_mapping: Optional[Dict[str, str]] = None):
        """
        Initialize filter service
        
        Args:
            default_mapping: Default key mapping to apply
        """
        self.default_mapping = default_mapping or {}
    
    def generate_score_mapping(self, extracted_filters: Dict[str, Any]) -> Dict[str, str]:
        """
        Auto-generate mapping for score fields following the pattern:
        {field}_score -> processed_{field}_score_001
        """
        mapping = {}
        for key in extracted_filters.keys():
            if key.endswith('_score'):
                field_name = key.replace('_score', '')
                mapped_key = f"processed_{field_name}_score_001"
                mapping[key] = mapped_key
        return mapping
    
    def transform_filter_values(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform filter values based on their type and field name:
        - float -> {'value': <value>, 'type': 'greater_equal'} (default)
        - list -> {'value': <value>, 'type': 'contains'}
        - max_price -> {'value': <value>, 'type': 'less_equal_than'}
        - min_price -> {'value': <value>, 'type': 'greater_equal'}
        - None values are skipped
        """
        transformed = {}
        
        for key, value in filters.items():
            if value is None:
                continue  # Skip None values
                
            if isinstance(value, (float, int)) and value is not None:
                # Special handling for price fields
                if key == 'max_price':
                    transformed[key] = {'value': value, 'type': 'less_equal_than'}
                elif key == 'min_price':
                    transformed[key] = {'value': value, 'type': 'greater_equal'}
                else:
                    # Default for other numeric fields (scores)
                    transformed[key] = {'value': value, 'type': 'greater_equal'}
            elif isinstance(value, list):
                transformed[key] = {'value': value, 'type': 'contains'}
            else:
                # Keep other values as-is (strings, already formatted dicts)
                transformed[key] = value
                
        return transformed
    
    def process_extracted_filters(self, 
                                extracted_filters: Dict[str, Any], 
                                additional_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Complete processing of extracted filters:
        1. Transform values by type
        2. Generate score field mappings
        3. Apply all mappings
        4. Exclude keywords from final output
        5. Return processed filters ready for merging
        """
        # Step 1: Transform values by type
        transformed = self.transform_filter_values(extracted_filters)
        
        # Step 2: Generate score mappings
        score_mapping = self.generate_score_mapping(extracted_filters)
        
        # Step 3: Combine with additional mapping and default mapping
        final_mapping = {}
        final_mapping.update(self.default_mapping)
        final_mapping.update(score_mapping)
        if additional_mapping:
            final_mapping.update(additional_mapping)
        
        # Step 4: Apply mapping if we have any
        if final_mapping:
            filters_obj = Filters.from_dict(transformed)
            mapped = filters_obj.apply_mapping(final_mapping)
            result = mapped.to_dict()
        else:
            result = transformed
        
        # Step 5: Remove non-filter fields from final output (but keep for extraction/logging)
        fields_to_exclude = ['keywords', 'search_type', 'place', 'sort_by']
        for field in fields_to_exclude:
            if field in result:
                del result[field]
        
        return result
    
    def merge_filters(self, 
                     existing_filters: Dict[str, Any], 
                     extracted_filters: Dict[str, Any], 
                     mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Merge extracted filters into existing filters, only overwriting empty values
        
        Args:
            existing_filters: The base filters (with potentially empty values)
            extracted_filters: The filters extracted from query
            mapping: Optional mapping to rename extracted filter keys
            
        Returns:
            Merged filters as dictionary
        """
        # Convert to Filters objects
        existing = Filters.from_dict(existing_filters)
        extracted = Filters.from_dict(extracted_filters)
        
        # Use provided mapping or default
        final_mapping = mapping or self.default_mapping
        
        # Merge filters
        result = existing.overwrite_empty_with(extracted, final_mapping)
        
        # Convert back to dict and return
        return result.to_dict()
    
    def apply_mapping_only(self, filters: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply mapping to filter keys without merging"""
        filters_obj = Filters.from_dict(filters)
        mapped = filters_obj.apply_mapping(mapping)
        return mapped.to_dict()
    
    def clean_empty_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Remove empty filters from the dictionary"""
        filters_obj = Filters.from_dict(filters)
        cleaned = filters_obj.remove_empty_filters()
        return cleaned.to_dict()
    
    def get_empty_filter_keys(self, filters: Dict[str, Any]) -> list:
        """Get list of empty filter keys"""
        filters_obj = Filters.from_dict(filters)
        return filters_obj.get_empty_keys()


# Example usage function
def example_usage():
    """Example of how to use the FilterService"""
    
    # Your existing filters (with empty cuisine type)
    existing_filters = {
        'status': {'value': ['OPERATIONAL'], 'type': 'is_in'},
        'processed_cuisine_type_001': {},  # Empty
        'processed_max_price_001': {'value': 20, 'type': 'less_equal_than'},
        'processed_min_price_001': {'value': 10, 'type': 'greater_equal'},
        'processed_avg_score_001': {'value': 4, 'type': 'greater_equal'},
        'sort_by': 'relevance'
    }
    
    # Filters extracted from natural language query
    extracted_filters = {
        'cuisine_type': {'value': 'italian', 'type': 'equals'},
        'price_range': {'value': 15, 'type': 'around'},
        'sort_by': 'relevance'
    }
    
    # Mapping to rename extracted filter keys
    mapping = {
        'cuisine_type': 'processed_cuisine_type_001',
        'price_range': 'processed_price_range_001'
    }
    
    # Create service
    filter_service = FilterService(default_mapping=mapping)
    
    # Merge filters
    result = filter_service.merge_filters(existing_filters, extracted_filters, mapping)
    
    print("Original existing filters:")
    print(existing_filters)
    print("\nExtracted filters:")
    print(extracted_filters)
    print("\nMerged result:")
    print(result)
    
    return result


if __name__ == "__main__":
    example_usage() 