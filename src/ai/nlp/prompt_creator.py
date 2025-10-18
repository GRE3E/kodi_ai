import logging
from datetime import datetime
from typing import Any
from src.ai.nlp.prompt_loader import load_system_prompt_template
from src.utils.datetime_utils import get_current_datetime, format_datetime, format_date_human_readable, format_time_only, get_country_from_timezone
import re

logger = logging.getLogger("PromptCreator")

def _safe_format_value(value: Any) -> str:
    """Convierte valores a strings seguros para formateo del system prompt."""
    if value is None:
        return "No disponible"
    if isinstance(value, dict):
        try:
            import json
            json_str = json.dumps(value, ensure_ascii=False)
            return json_str
        except:
            return ", ".join([f"{k}: {_safe_format_value(v)}" for k, v in value.items()])
    if isinstance(value, (list, tuple)):
        try:
            import json
            json_str = json.dumps(value, ensure_ascii=False)
            return json_str
        except:
            return ", ".join([_safe_format_value(item) for item in value])
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return str(value).lower()
    
    result = str(value)
    
    if (result.startswith('{') and result.endswith('}')) or (result.startswith('[') and result.endswith(']')):
        try:
            import json
            json.loads(result)
            return result
        except:
            pass
    
    result = result.replace("{", "{{").replace("}", "}}")
    result = ''.join(char for char in result if ord(char) >= 32 or char in '\n\r\t')
    return result

def create_system_prompt(
    config: dict,
    user_id: int,
    user_name: str,
    user_email: str,
    user_username: str,
    user_permissions_str: str,
    destino_favorito: Any,
    ubicacion_favorita: Any,
    categoria_favorita: Any,
    no_le_gusta: Any,
    user_budget: Any,
    current_date: str,
    current_time: str,
    current_location: str,
    available_destinations: list,
    travelerTypes: Any = None,
    travelingWith: Any = None,
    travelDuration: Any = None,
    activities: Any = None,
    placeTypes: Any = None,
    budget: Any = None,
    transport: Any = None,
) -> str:
    """
    Crea el system_prompt y el prompt_text para Ollama.
    """
    logger.debug("Construyendo system_prompt para Ollama.")
    
    timezone_str = config.get("timezone", "UTC")
    current_full_datetime = get_current_datetime(timezone_str)
    current_date_formatted = format_date_human_readable(current_full_datetime)
    current_time_formatted = format_time_only(current_full_datetime)
    current_country = get_country_from_timezone(timezone_str)

    system_prompt_template = load_system_prompt_template()
    
    system_prompt = system_prompt_template.format(
        assistant_name=config["assistant_name"],
        language=config["language"],
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        user_username=user_username,
        user_permissions=user_permissions_str,
        current_date=current_date_formatted,
        current_time=current_time_formatted,
        current_country=current_country,
        destino_favorito=_safe_format_value(destino_favorito),
        ubicacion_favorita=_safe_format_value(ubicacion_favorita),
        categoria_favorita=_safe_format_value(categoria_favorita),
        no_le_gusta=_safe_format_value(no_le_gusta),
        preferencia_precio=_safe_format_value(user_budget),
        available_destinations=_safe_format_value(available_destinations),
        travelerTypes=_safe_format_value(travelerTypes),
        travelingWith=_safe_format_value(travelingWith),
        travelDuration=_safe_format_value(travelDuration),
        activities=_safe_format_value(activities),
        placeTypes=_safe_format_value(placeTypes),
        budget=_safe_format_value(budget),
        transport=_safe_format_value(transport),
    )
    
    return system_prompt