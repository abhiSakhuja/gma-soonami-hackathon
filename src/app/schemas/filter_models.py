from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List
import copy


@dataclass
class FilterValue:
    """Represents a single filter with value and type"""
    value: Union[str, int, float, List[str]]
    type: str
    
    def is_empty(self) -> bool:
        """Check if the filter value is empty or meaningless"""
        if self.value is None:
            return True
        if isinstance(self.value, (list, dict)) and len(self.value) == 0:
            return True
        if isinstance(self.value, str) and self.value.strip() == "":
            return True
        return False


@dataclass
class Filters:
    """Main filters dataclass with methods for manipulation"""
    filters: Dict[str, Union[FilterValue, Dict[str, Any]]] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Filters':
        """Create Filters instance from dictionary"""
        filters_dict = {}
        
        # Define fields that should be excluded from filters
        excluded_fields = {'sort_by', 'search_type', 'place', 'keywords'}
        
        for key, value in data.items():
            if key in excluded_fields:
                continue
                
            if isinstance(value, dict) and 'value' in value and 'type' in value:
                filters_dict[key] = FilterValue(value=value['value'], type=value['type'])
            else:
                filters_dict[key] = value
                
        return cls(filters=filters_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert back to dictionary format"""
        result = {}
        
        for key, value in self.filters.items():
            if isinstance(value, FilterValue):
                result[key] = {"value": value.value, "type": value.type}
            else:
                result[key] = value
                
        return result
    
    def get_empty_keys(self) -> List[str]:
        """Get list of keys that have empty values"""
        empty_keys = []
        for key, value in self.filters.items():
            if isinstance(value, FilterValue) and value.is_empty():
                empty_keys.append(key)
            elif isinstance(value, dict) and len(value) == 0:
                empty_keys.append(key)
        return empty_keys
    
    def apply_mapping(self, mapping: Dict[str, str]) -> 'Filters':
        """Apply key mapping to filter names"""
        new_filters = copy.deepcopy(self)
        mapped_filters = {}
        
        for key, value in new_filters.filters.items():
            # Use mapped key if exists, otherwise keep original
            mapped_key = mapping.get(key, key)
            mapped_filters[mapped_key] = value
            
        new_filters.filters = mapped_filters
        return new_filters
    
    def overwrite_empty_with(self, source_filters: 'Filters', mapping: Optional[Dict[str, str]] = None) -> 'Filters':
        """
        Overwrite empty/missing values with values from source_filters
        
        Args:
            source_filters: The source filters to take values from
            mapping: Optional mapping to rename keys during overwrite
        """
        result = copy.deepcopy(self)
        
        # Apply mapping to source filters if provided
        if mapping:
            mapped_source = source_filters.apply_mapping(mapping)
        else:
            mapped_source = source_filters
        
        # Get empty keys in current filters
        empty_keys = result.get_empty_keys()
        
        # Overwrite empty values and add missing keys
        for key, value in mapped_source.filters.items():
            # Skip if the value in source is also empty
            if isinstance(value, FilterValue) and value.is_empty():
                continue
            if isinstance(value, dict) and len(value) == 0:
                continue
                
            # Overwrite if key is empty or missing
            if key in empty_keys or key not in result.filters:
                result.filters[key] = copy.deepcopy(value)
        
        return result
    
    def update_filter(self, key: str, value: Any, filter_type: str) -> None:
        """Update a specific filter"""
        self.filters[key] = FilterValue(value=value, type=filter_type)
    
    def remove_empty_filters(self) -> 'Filters':
        """Remove all empty filters"""
        result = copy.deepcopy(self)
        result.filters = {
            key: value for key, value in result.filters.items()
            if not (isinstance(value, FilterValue) and value.is_empty()) and
               not (isinstance(value, dict) and len(value) == 0)
        }
        return result
    
    def __repr__(self) -> str:
        return f"Filters(filters={self.filters})" 