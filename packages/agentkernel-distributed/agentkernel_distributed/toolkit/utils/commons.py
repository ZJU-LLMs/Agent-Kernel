"""Common utility functions for the toolkit."""

import re
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError


def clean_json_response(response: Optional[str]) -> str:
    """
    Strip Markdown code fences from a JSON response emitted by an LLM.

    Args:
        response (Optional[str]): Raw response string containing optional `````json`` fences.

    Returns:
        str: Sanitised JSON string with leading/trailing fences removed.
    """
    if response is None:
        return ""

    if response.strip().startswith("```json"):
        response = response.strip()[7:]
    if response.strip().endswith("```"):
        response = response.strip()[:-3]
    return response.strip()


def clean_think_tag(response: str) -> str:
    """
    Remove ``<think>...</think>`` tags from a model response.

    Args:
        response (str): Raw response containing optional think tags.

    Returns:
        str: Response with think tags removed.
    """
    return re.sub(r"<think>.*?</think>", "", response, flags=re.S)


def remove_none_values(data: Any) -> Any:
    """
    Recursively remove keys whose value is ``None`` from dictionaries/lists.

    Args:
        data (Any): Arbitrary data structure containing nested dictionaries or lists.

    Returns:
        Any: Structure with ``None`` entries removed.
    """
    if isinstance(data, dict):
        return {key: remove_none_values(value) for key, value in data.items() if value is not None}
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data]
    else:
        return data


def resolve_name(current_name: Optional[str], valid_names: List[str]) -> str:
    """
    Resolve a name against a list of valid names.

    Args:
        current_name (Optional[str]): The name to resolve (can be partial).
        valid_names (List[str]): List of valid full names.

    Returns:
        str: The matching valid name.

    Raises:
        ValidationError: If name is empty, not found, or ambiguous.
    """
    if not current_name or not current_name.strip():
        raise ValidationError("Input name cannot be empty.")

    normalized_current_name = current_name.lower().strip()

    possible_matches = []
    for name in valid_names:
        normalized_name = name.lower().strip()
        if normalized_current_name == normalized_name:
            return name  # Exact match found, return the correct name
        elif normalized_current_name in normalized_name:
            possible_matches.append(name)

    if len(possible_matches) == 1:
        return possible_matches[0]  # Unique partial match found
    elif len(possible_matches) > 1:
        raise ValidationError(
            f"Name '{current_name}' is ambiguous and matches multiple valid names: {possible_matches}"
        )
    else:
        raise ValidationError(f"Name '{current_name}' could not be found in the list of valid names.")


def clean_empty_fields(data: Any) -> Any:
    """
    Recursively remove empty fields (``None``, `{}`, `[]`) from a data structure.
    This function traverses nested dictionaries, lists, and tuples, removing
    any keys or items that are ``None`` or become empty containers after cleaning.
    It can also handle custom objects that have ``to_dict()`` or ``__dict__`` attributes.

    Args:
        data (Any): The data structure to clean, such as a dictionary, list, or object.

    Returns:
        Any: The data structure with all empty fields removed.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            cleaned_value = clean_empty_fields(value)
            if cleaned_value is not None and cleaned_value != {} and cleaned_value != []:
                cleaned[key] = cleaned_value
        return cleaned
    elif isinstance(data, (list, tuple)):
        cleaned_items = []
        for item in data:
            cleaned_item = clean_empty_fields(item)
            if cleaned_item is not None and cleaned_item != {} and cleaned_item != []:
                cleaned_items.append(cleaned_item)
        if isinstance(data, tuple):
            return tuple(cleaned_items)
        return cleaned_items
    elif hasattr(data, "to_dict"):
        try:
            dict_data = data.to_dict()
            return clean_empty_fields(dict_data)
        except Exception:
            return data
    elif hasattr(data, "__dict__"):
        try:
            dict_data = data.__dict__
            cleaned_dict = clean_empty_fields(dict_data)
            return cleaned_dict
        except Exception:
            return data
    else:
        return data
