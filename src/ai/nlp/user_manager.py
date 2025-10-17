import asyncio
import logging
import re
from typing import Optional
import httpx
import json
from pathlib import Path

logger = logging.getLogger("UserManager")

HISTORY_DIR = Path("data")
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

class UserManager:
    """
    Gestiona la lógica relacionada con usuarios, permisos y preferencias.
    """
    def __init__(self):
        self._last_recommendation = {}

    async def save_recommendation_to_api(self, user_id: str, recommendation_data: dict, auth_token: str) -> Optional[str]:
        """
        Guarda la recomendación en /api/recomendaciones-ia con aceptada=false.
        Retorna el ID de la recomendación creada.
        
        Args:
            user_id: ID del usuario
            recommendation_data: Diccionario con los datos de la recomendación
            auth_token: Token de autenticación
            
        Returns:
            recommendation_id si fue exitoso, None si hubo error
        """
        recommendations_api_url = "http://localhost:3001/api/recomendaciones-ia"
        try:
            payload = {
                "userId": str(user_id),
                "destinationId": recommendation_data.get("destinationId"),
                "tipo": recommendation_data.get("tipo", "basado_en_preferencias"),
                "aceptada": False
            }
            
            if not payload["destinationId"]:
                logger.warning(f"Recomendación sin 'destinationId', no se registrará: {recommendation_data}")
                return None

            headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
            logger.info(f"Guardando recomendación en API con aceptada=false: {payload}")

            async with httpx.AsyncClient() as client:
                response = await client.post(recommendations_api_url, json=payload, headers=headers)
                response.raise_for_status()
                response_data = response.json()
                recommendation_id = response_data.get("id")

                logger.info(f"Recomendación guardada en API con ID: {recommendation_id}")
                return recommendation_id

        except httpx.RequestError as e:
            logger.error(f"Error de red al guardar recomendación para {user_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al guardar recomendación para {user_id}: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al guardar recomendación para {user_id}: {e}")
            return None

    async def save_last_recommendation(self, user_id: str, recommendation_data: dict) -> None:
        """
        Guarda la última recomendación SOLO en memoria (no llama a API).
        
        Args:
            user_id: ID del usuario
            recommendation_data: Diccionario con los datos de la recomendación (debe incluir recommendation_id)
        """
        self._last_recommendation[user_id] = recommendation_data
        logger.info(f"Recomendación guardada en memoria para {user_id}: {recommendation_data}")

    async def get_last_recommendation(self, user_id: str) -> Optional[dict]:
        """Recupera la última recomendación generada para un usuario desde memoria."""
        recommendation = self._last_recommendation.get(user_id)
        if recommendation:
            logger.info(f"Recuperando última recomendación para {user_id}: {recommendation}")
        else:
            logger.warning(f"No hay recomendación previa para {user_id}")
        return recommendation

    async def get_user_data_by_id(self, user_id: str, auth_token: str) -> tuple[Optional[dict], str, dict]:
        """
        Recupera los datos del usuario.
        """
        logger.debug(f"Intentando recuperar datos de usuario para user_id: {user_id}")
        
        user_data_container = {
            "id": user_id,
            "nombre": "Desconocido",
            "preferences_str": "",
            "preferences_dict": {}
        }

        user_preferences_url = f"http://localhost:3001/api/user-preferences/preferences/{user_id}"
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {auth_token}"}
                response = await client.get(user_preferences_url, headers=headers)
                response.raise_for_status()
                preferences_data = response.json()
                logger.debug(f"API response for user preferences: {preferences_data}")
                
                if preferences_data and isinstance(preferences_data, list) and len(preferences_data) > 0:
                    first_preference = preferences_data[0]
                    
                    user_data_container["nombre"] = first_preference.get("profile", {}).get("name", user_data_container["nombre"])
                    user_data_container["email"] = first_preference.get("user", {}).get("email", user_data_container.get("email"))
                    user_data_container["username"] = first_preference.get("user", {}).get("username", user_data_container.get("username"))

                    dynamic_preferences_str = []
                    dynamic_preferences_dict = {}

                    if first_preference.get("destinationName"):
                        dynamic_preferences_str.append(f"destino_favorito: {first_preference['destinationName']}")
                        dynamic_preferences_dict["destino_favorito"] = first_preference['destinationName']
                    if first_preference.get("location"):
                        dynamic_preferences_str.append(f"ubicacion_favorita: {first_preference['location']}")
                        dynamic_preferences_dict["ubicacion_favorita"] = first_preference['location']
                    if first_preference.get("category"):
                        dynamic_preferences_str.append(f"categoria_favorita: {first_preference['category']}")
                        dynamic_preferences_dict["categoria_favorita"] = first_preference['category']
                    if first_preference.get("precio") is not None:
                        dynamic_preferences_str.append(f"preferencia_precio: {first_preference['precio']}")
                        dynamic_preferences_dict["preferencia_precio"] = first_preference['precio']
                    if first_preference.get("unliked"):
                        dynamic_preferences_str.append(f"no_le_gusta: {first_preference['unliked']}")
                        dynamic_preferences_dict["no_le_gusta"] = first_preference['unliked']
                    if first_preference.get("interestType"):
                        dynamic_preferences_str.append(f"tipo_interes: {first_preference['interestType']}")
                        dynamic_preferences_dict["tipo_interes"] = first_preference['interestType']
                    if first_preference.get("preferredDuration"):
                        dynamic_preferences_str.append(f"duracion_preferida: {first_preference['preferredDuration']}")
                        dynamic_preferences_dict["duracion_preferida"] = first_preference['preferredDuration']
                    if first_preference.get("geographicalFocus"):
                        dynamic_preferences_str.append(f"enfoque_geografico: {first_preference['geographicalFocus']}")
                        dynamic_preferences_dict["enfoque_geografico"] = first_preference['geographicalFocus']
                    if dynamic_preferences_str:
                        user_data_container["preferences_str"] = ", ".join(dynamic_preferences_str)
                    if dynamic_preferences_dict:
                        user_data_container["preferences_dict"] = dynamic_preferences_dict

                    logger.info(f"Preferencias de usuario cargadas dinámicamente para {user_id}: {user_data_container['preferences_dict']}")
                else:
                    logger.warning(f"No se encontraron preferencias para el usuario {user_id} en el endpoint. Usando valores por defecto.")

        except httpx.RequestError as e:
            logger.error(f"Error de red o conexión al obtener preferencias para {user_id}: {e}. Usando valores por defecto.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener preferencias para {user_id}: {e}. Usando valores por defecto.")
        except json.JSONDecodeError:
            logger.error(f"Error al decodificar JSON de preferencias para {user_id}. Usando valores por defecto.")
        except Exception as e:
            logger.error(f"Error inesperado al obtener preferencias para {user_id}: {e}. Usando valores por defecto.")

        user_permissions_str = user_data_container.get("permissions", "")
        user_preferences_dict = user_data_container.get("preferences_dict", {})

        return user_data_container, user_permissions_str, user_preferences_dict

    async def handle_preference_setting(self, user_data: dict, full_response_content: str, auth_token: str) -> str:
        """
        Limpia los marcadores JSON del contenido visible al usuario.
        """
        user_id = user_data.get("id")
        if not user_id:
            logger.error("No se pudo obtener user_id de user_data para handle_preference_setting.")
            return full_response_content
        recommendation_pattern = re.compile(
            r"(?:GENERAR_RECOMENDACION_JSON:\s*{.*?}|```json\s*{.*?}\s*```|Generar recomendación JSON:[\s\S]*?```json[\s\S]*?```)",
            re.DOTALL | re.IGNORECASE
        )
        cleaned_response_content = recommendation_pattern.sub("", full_response_content).strip()
        cleaned_response_content = re.sub(r"\n---\s*$", "", cleaned_response_content).strip()
        cleaned_response_content = re.sub(r"\n{3,}", "\n\n", cleaned_response_content)
        
        return cleaned_response_content if cleaned_response_content else full_response_content

    def _get_history_file_path(self, user_id: str) -> Path:
        """Obtiene la ruta del archivo de historial para un user_id dado."""
        return HISTORY_DIR / f"{user_id}_history.json"

    def load_conversation_history(self, user_id: str) -> list[dict]:
        """Carga el historial de conversación de un usuario desde un archivo JSON."""
        history_file = self._get_history_file_path(user_id)
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    logger.debug(f"Historial cargado para {user_id}: {len(history)} mensajes.")
                    return history
            except json.JSONDecodeError:
                logger.warning(f"Archivo de historial corrupto para {user_id}. Iniciando historial vacío.")
        return []

    def save_conversation_history(self, user_id: str, history: list[dict]) -> None:
        """Guarda el historial de conversación de un usuario en un archivo JSON."""
        history_file = self._get_history_file_path(user_id)
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
            logger.debug(f"Historial guardado para {user_id}: {len(history)} mensajes.")
        except IOError as e:
            logger.error(f"Error al guardar el historial para {user_id}: {e}")
