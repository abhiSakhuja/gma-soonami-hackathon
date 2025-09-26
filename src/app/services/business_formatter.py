def format_business_metadata(business):
    """
    Formats business metadata into a structured text suitable for LLM input.

    Parameters:
    - business (dict): A dictionary containing business metadata.

    Returns:
    - str: A formatted string representing the business information.
    """
    # Extract relevant fields with defaults
    business_id = business.get('business_id', 'N/A')
    summary = business.get('business_summary', 'No summary available.')
    cuisine_types = ', '.join(business.get('cuisine_type', {}).get("main_cuisine_types", [])) or 'Not specified'
    price_range = business.get('price_range', 'Not specified')
    min_price = business.get('min_price', 'N/A')
    max_price = business.get('max_price', 'N/A')
    ## TODO: Modify when all cases have the same format
    must_try = ', '.join(business.get('must_try', {}).keys() if isinstance(business.get('must_try'), dict) else business.get('must_try', [])) or 'None listed'
    must_avoid = ', '.join(business.get('must_avoid', {}).keys() if isinstance(business.get('must_avoid'), dict) else business.get('must_avoid', [])) or 'None listed'


    # Construct the formatted string
    formatted_text = (
        f"Business ID: {business_id}\n"
        f"Summary: {summary}\n"
        f"Cuisine Types: {cuisine_types}\n"
        f"Price Range: {price_range} (Min: €{min_price}, Max: €{max_price})\n"
        f"Must-Try Dishes: {must_try}\n"
        f"Must-Avoid Items: {must_avoid}\n"
    )

    return formatted_text
