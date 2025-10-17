import requests
import logging

logger = logging.getLogger(__name__)

DESTINATIONS_API_URL = "http://localhost:3001/api/destinations"

def get_all_destinations():
    """
    Fetches all destinations from the destinations API.
    """
    logger.info(f"Utilizando endpoint: {DESTINATIONS_API_URL}")
    try:
        response = requests.get(DESTINATIONS_API_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching destinations from API: {e}")
        return None

def get_destinations_by_budget(max_budget: float):
    """
    Fetches destinations and filters them by a maximum budget.
    """
    logger.info(f"Utilizando endpoint de destinos por presupuesto: {DESTINATIONS_API_URL}")
    all_destinations = get_all_destinations()
    if all_destinations:
        filtered_destinations = []
        for d in all_destinations:
            if d.get("status") and d.get("precio") is not None and d.get("precio") <= max_budget:
                filtered_destinations.append({
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "location": d.get("location"),
                    "latitude": d.get("latitude"),
                    "longitude": d.get("longitude"),
                    "precio": d.get("precio"),
                    "category": d.get("category"),
                    "status": d.get("status"),
                    "createdAt": d.get("createdAt"),
                    "updatedAt": d.get("updatedAt"),
                    "status_code": d.get("status_code")
                })
        return filtered_destinations
    return []