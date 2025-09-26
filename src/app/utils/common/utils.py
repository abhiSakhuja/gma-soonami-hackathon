from functools import wraps
import os
import tarfile
import logging
from typing import Dict, Any


def retry(max_retries=3, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Exception occurred: {e}. Retrying...")
                    retries += 1
            raise Exception("Max retries exceeded. Could not process reviews.")
        return wrapper
    return decorator

def get_params_from_event(event: Dict[str, Any], param_keys, exclude_nulls=True):
    """
    Extract specified parameters from an event data dictionary.

    This function retrieves the values associated with the specified keys from
    the given event data dictionary. It can optionally exclude keys with `None`
    values.

    :param event_data: The dictionary containing event data.
    :type event_data: dict
    :param param_keys: A list of keys whose values need to be extracted from the event data.
    :type param_keys: list
    :param exclude_nulls: If True, keys with `None` values will be excluded from the result (default is True).
    :type exclude_nulls: bool
    :return: A dictionary containing the specified keys and their corresponding values from the event data.
             Keys with `None` values are excluded if `exclude_nulls` is True.
    :rtype: dict

    Example:
    >>> event_data = {'a': 1, 'b': None, 'c': 3, 'd': 0, 'e': False}
    >>> param_keys = ['a', 'b', 'c', 'd', 'e']
    >>> get_params_from_event(event_data, param_keys)
    {'a': 1, 'c': 3, 'd': 0, 'e': False}
    >>> get_params_from_event(event_data, param_keys, exclude_nulls=False)
    {'a': 1, 'b': None, 'c': 3, 'd': 0, 'e': False}
    """
    params = {}
    for k in param_keys:
        value = event.get(k)
        if not exclude_nulls or value is not None:
            params[k] = value
    return params

def extract_tar_gz_file(file_path, output_dir: str, logger=None):
    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        # Ensure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.debug(f"Created output directory: {output_dir}")

        # Open the .tar.gz file
        with tarfile.open(file_path, 'r:gz') as tar:
            # Extract all contents to the output directory
            tar.extractall(path=output_dir)
            logger.debug(f"Files extracted to: {output_dir}")
            
            # Optionally, list the extracted files for verification
            # extracted_files = os.listdir(output_dir)
            # logger.debug(f"Extracted files: {extracted_files}")

    except Exception as e:
        logger.error(f"Error extracting .tar.gz file: {e}")
        return None

    # Delete the .tar.gz file
    try:
        os.remove(file_path)
        logger.debug(f".tar.gz file {file_path} deleted.")
    except Exception as e:
        logger.error(f"Error deleting .tar.gz file: {e}")

    return output_dir

def filter_dicts(dict_list, keys_to_keep):
    """
    Filters a list of dictionaries to keep only the specified keys.

    Parameters:
    - dict_list (list of dict): The list of dictionaries to filter.
    - keys_to_keep (set or list): The keys to retain in each dictionary.

    Returns:
    - list of dict: The filtered list of dictionaries.
    """
    return [{k: d[k] for k in keys_to_keep if k in d} for d in dict_list]

def update_filters(existing_filters: dict, new_filters: dict, mapping: dict) -> dict:
    """
    Updates all filters with mapped keys where applicable, applying standard rules.
    
    The function applies:
    - "is_in" type for lists.
    - "equals" type for strings or integers.
    
    Args:
        existing_filters (dict): The original dictionary with applied filters.
        new_filters (dict): The dictionary with updated filters from the LLM.
        mapping (dict): A dictionary that maps new filter names to existing filter names.
    
    Returns:
        dict: The updated filters dictionary with mapped keys and applied rules.
    """
    updated_filters = existing_filters.copy()

    for new_key, new_value in new_filters.items():
        target_key = mapping.get(new_key, new_key)  # Use mapped key if available

        if isinstance(new_value, list):
            updated_filters[target_key] = {
                "value": new_value,
                "type": "is_in"
            }
        elif isinstance(new_value, (str, int)):
            updated_filters[target_key] = {
                "value": new_value,
                "type": "equals"
            }

    return updated_filters



def merge_dicts_by_id(primary_list: list, secondary_list: list, id_key: str) -> list:
    """
    Merges two lists of dictionaries, keeping all dictionaries from the secondary list and 
    extending them with values from the primary list based on a shared ID key.

    Args:
        primary_list (list): The list containing additional key-value pairs.
        secondary_list (list): The list to be extended with values from primary_list.
        id_key (str): The key used to join the dictionaries.

    Returns:
        list: A merged list where each dictionary in secondary_list is extended with matching data from primary_list.
    """
    
    # Create a lookup dictionary from primary_list using id_key
    primary_lookup = {item[id_key]: item for item in primary_list}

    # Iterate over secondary_list and extend with matching data from primary_lookup
    merged_list = []
    for sec_dict in secondary_list:
        sec_id = sec_dict.get(id_key)

        if sec_id in primary_lookup:
            # Merge dictionaries (secondary takes priority)
            merged_dict = {**primary_lookup[sec_id], **sec_dict}
        else:
            merged_dict = sec_dict  # Keep as-is if no match
        
        merged_list.append(merged_dict)

    return merged_list

