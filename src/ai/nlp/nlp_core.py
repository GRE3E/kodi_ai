import asyncio
import logging
import re
from typing import Optional, Any
from pathlib import Path
from ollama import AsyncClient, ResponseError
from httpx import ConnectError
from datetime import datetime
from contextlib import asynccontextmanager
import json
from src.ai.nlp.ollama_manager import OllamaManager
from src.ai.nlp.config_manager import ConfigManager
from src.ai.nlp.user_manager import UserManager
from src.ai.nlp.prompt_creator import create_system_prompt
from src.utils.datetime_utils import (
    get_current_datetime,
    format_date_human_readable,
    format_time_only,
    get_country_from_timezone,
)
from src.utils.destination_api import get_destinations_by_budget
import httpx
from datetime import timedelta

logger = logging.getLogger("NLPModule")

PREFERENCE_MARKERS_REGEX = re.compile(r"(preference_set:)")
ACCEPTANCE_PHRASES_REGEX = re.compile(r"\b(aceptar|sí|ok|confirmar|si|perfecto|excelente)\b|\bagend[a-z]*\b|\b(usa mis datos|registra en mi agenda|guardalo)\b", re.IGNORECASE)
RECOMMENDATION_JSON_REGEX = re.compile(
    r"(?:GENERAR_RECOMENDACION_JSON:\s*({.*?})|```json\s*({.*?})\s*```)",
    re.DOTALL | re.IGNORECASE
)

class NLPModule:
    """Clase principal para el procesamiento NLP con integración a Ollama."""

    def __init__(self):
        self._ollama_manager = None
        print(f"DEBUG: NLPModule initialized.")
        """Inicializa configuración, OllamaManager y UserManager."""
        self._config_path = Path(__file__).parent.parent / "config" / "config.json"
        self._config_manager = ConfigManager(self._config_path)
        self._config = self._config_manager.get_config()
        self._ollama_manager = OllamaManager(self._config["model"])
        self._online = self._ollama_manager.is_online()
        self._user_manager = UserManager()
        self._conversation_history = {}
        logger.info("NLPModule inicializado.")

    def __del__(self) -> None:
        """Libera recursos al destruir la instancia."""
        logger.info("Cerrando NLPModule.")
        del self._ollama_manager

    def is_online(self) -> bool:
        """Devuelve True si el módulo NLP está online."""
        return self._ollama_manager.is_online()

    def reload(self) -> None:
        """Recarga configuración y valida conexión."""
        logger.info("Recargando NLPModule...")
        self._config_manager.load_config()
        self._config = self._config_manager.get_config()
        self._ollama_manager.reload(self._config["model"])
        self._online = self._ollama_manager.is_online()
        log_fn = logger.info if self._online else logger.warning
        log_fn("NLPModule recargado." if self._online else "NLPModule recargado pero no en línea.")

    async def generate_response(self, prompt: str, userId: int, auth_token: str) -> Optional[dict]:
        """Genera una respuesta usando Ollama, gestionando memoria y permisos."""
        logger.info(f"Generando respuesta para el prompt: '{prompt[:100]}...' (Usuario ID: {userId})")

        if not prompt or not prompt.strip():
            return {
                "response": "El prompt no puede estar vacío.",
                "error": "Prompt vacío",
                "user_name": "",
                "preference_key": None,
                "preference_value": None,
            }

        if not self.is_online():
            try:
                self.reload()
                if not self.is_online():
                    return {
                        "response": "El módulo NLP está fuera de línea.",
                        "error": "Módulo NLP fuera de línea",
                        "user_name": "",
                        "preference_key": None,
                        "preference_value": None,
                    }
            except Exception as e:
                return {
                    "response": f"El módulo NLP está fuera de línea: {e}",
                    "error": "Módulo NLP fuera de línea",
                    "user_name": "",
                    "preference_key": None,
                    "preference_value": None,
                }

        if userId is None:
            return {
                "response": "userId es requerido para consultas NLP.",
                "error": "userId es requerido",
                "user_name": "",
                "preference_key": None,
                "preference_value": None,
            }

        user_data_container, user_permissions_str, user_preferences_dict = await self._user_manager.get_user_data_by_id(userId, auth_token)

        if not user_data_container:
            return {
                "response": "Usuario no autorizado o no encontrado.",
                "error": "Usuario no autorizado o no encontrado.",
                "user_name": None,
                "preference_key": None,
                "preference_value": None,
                "command": None,
            }

        # --- Lógica para manejar la aceptación de recomendaciones ---
        if ACCEPTANCE_PHRASES_REGEX.search(prompt):
            logger.info(f"Prompt de usuario indica aceptación: {prompt}")
            last_recommendation = await self._user_manager.get_last_recommendation(userId)

            if last_recommendation:
                logger.info(f"Última recomendación encontrada para {userId}: {last_recommendation}")
                
                recommendation_id = last_recommendation.get("recommendation_id")
                if not recommendation_id:
                    logger.error(f"No se encontró recommendation_id en la última recomendación")
                    return {
                        "response": "Lo siento, hubo un error al procesar tu aceptación. Intenta nuevamente.",
                        "user_name": user_data_container.get("nombre"),
                        "preference_key": None,
                        "preference_value": None,
                        "command": None,
                    }
                
                update_recommendation_url = f"http://localhost:3001/api/recomendaciones-ia/{recommendation_id}"
                logger.info(f"Actualizando recomendación {recommendation_id} a aceptada=true")
                
                try:
                    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
                    async with httpx.AsyncClient() as client:
                        patch_response = await client.patch(
                            update_recommendation_url, 
                            json={"aceptada": True}, 
                            headers=headers
                        )
                        patch_response.raise_for_status()
                        logger.info(f"Recomendación {recommendation_id} actualizada a aceptada=true")
                        
                        agenda_api_url = "http://localhost:3001/api/agenda"
                        scheduled_at = (datetime.now() + timedelta(days=1)).isoformat() + "Z"
                        agenda_payload = {
                            "userId": str(userId),
                            "destinationId": last_recommendation["destinationId"],
                            "scheduledAt": scheduled_at,
                            "status": "PENDING",
                        }
                        
                        logger.info(f"Guardando en agenda: {agenda_payload}")
                        agenda_response = await client.post(agenda_api_url, json=agenda_payload, headers=headers)
                        agenda_response.raise_for_status()
                        logger.info(f"Recomendación guardada en agenda exitosamente para {userId}")
                        
                        return {
                            "response": "Excelente. He agendado tu viaje. Que lo disfrutes.",
                            "user_name": user_data_container.get("nombre"),
                            "preference_key": None,
                            "preference_value": None,
                            "command": f"AGENDA_RECOMMENDATION:{json.dumps(agenda_payload)}",
                        }
                        
                except httpx.RequestError as e:
                    logger.error(f"Error de red al procesar aceptación para {userId}: {e}")
                    return {
                        "response": f"Lo siento, no pude procesar tu aceptación debido a un error de conexión.",
                        "user_name": user_data_container.get("nombre"),
                        "preference_key": None,
                        "preference_value": None,
                        "command": None,
                    }
                except httpx.HTTPStatusError as e:
                    logger.error(f"Error HTTP al procesar aceptación para {userId}: {e.response.status_code} - {e.response.text}")
                    return {
                        "response": f"Lo siento, hubo un problema al procesar tu aceptación: {e.response.status_code}",
                        "user_name": user_data_container.get("nombre"),
                        "preference_key": None,
                        "preference_value": None,
                        "command": None,
                    }
                except Exception as e:
                    logger.error(f"Error inesperado al procesar aceptación para {userId}: {e}")
                    return {
                        "response": f"Lo siento, ocurrió un error inesperado: {e}",
                        "user_name": user_data_container.get("nombre"),
                        "preference_key": None,
                        "preference_value": None,
                        "command": None,
                    }
            else:
                logger.warning(f"No se encontró ninguna recomendación previa para agendar para el usuario {userId}.")
                return {
                    "response": "No hay ninguna recomendación reciente para agendar. ¿Te gustaría que te sugiera algo?",
                    "user_name": user_data_container.get("nombre"),
                    "preference_key": None,
                    "preference_value": None,
                    "command": None,
                }

        retries = 2
        client = AsyncClient(host="http://localhost:11434")

        user_conversation_history = self._user_manager.load_conversation_history(userId)

        timezone = self._config.get("timezone", "UTC")
        current_datetime = get_current_datetime(timezone)
        current_date = format_date_human_readable(current_datetime)
        current_time = format_time_only(current_datetime)
        current_location = get_country_from_timezone(timezone)

        user_budget = user_preferences_dict.get("preferencia_precio")
        available_destinations = []
        if user_budget is not None:
            available_destinations = json.dumps(get_destinations_by_budget(user_budget))

        system_prompt = create_system_prompt(
            config=self._config,
            user_id=userId,
            user_name=user_data_container.get("nombre"),
            user_email=user_data_container.get("email"),
            user_username=user_data_container.get("username"),
            user_permissions_str=user_permissions_str,
            destino_favorito=user_preferences_dict.get("destino_favorito"),
            ubicacion_favorita=user_preferences_dict.get("ubicacion_favorita"),
            categoria_favorita=user_preferences_dict.get("categoria_favorita"),
            no_le_gusta=user_preferences_dict.get("no_le_gusta"),
            user_budget=user_budget,
            current_date=current_date,
            current_time=current_time,
            current_location=current_location,
            available_destinations=available_destinations,
            travelerTypes=user_preferences_dict.get("travelerTypes"),
            travelingWith=user_preferences_dict.get("travelingWith"),
            travelDuration=user_preferences_dict.get("travelDuration"),
            activities=user_preferences_dict.get("activities"),
            placeTypes=user_preferences_dict.get("placeTypes"),
            budget=user_preferences_dict.get("budget"),
            transport=user_preferences_dict.get("transport"),
        )

        for attempt in range(retries):
            user_conversation_history.append({"role": "user", "content": prompt})

            messages = [
                {"role": "system", "content": system_prompt},
            ] + user_conversation_history

            full_response_content, llm_error = await self._get_llm_response(client, messages)
            if llm_error:
                if attempt == retries - 1:
                    return {
                        "response": llm_error,
                        "error": llm_error,
                        "user_name": user_data_container.get("nombre"),
                        "preference_key": None,
                        "preference_value": None,
                        "command": None,
                    }
                continue

            user_conversation_history.append({"role": "assistant", "content": full_response_content})
            command_to_return = None
            is_recommendation = re.search(r"\*\*Destino:\*\*|\*\*Ubicación:\*\*|\*\*Presupuesto:\*\*", full_response_content)
            recommendation_match = RECOMMENDATION_JSON_REGEX.search(full_response_content)
            
            if recommendation_match:
                try:
                    recommendation_json_str = recommendation_match.group(1) or recommendation_match.group(2)
                    command_to_return = recommendation_match.group(0)
                    recommendation_data = json.loads(recommendation_json_str)
                    recommendation_id = await self._user_manager.save_recommendation_to_api(
                        userId, 
                        recommendation_data, 
                        auth_token
                    )
                    
                    if recommendation_id:
                        recommendation_data["recommendation_id"] = recommendation_id
                        await self._user_manager.save_last_recommendation(userId, recommendation_data)
                        logger.info(f"Recomendación guardada completamente para {userId}: {recommendation_data}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error al decodificar JSON de recomendación para el usuario {userId}: {e}")
                except Exception as e:
                    logger.error(f"Error inesperado al procesar JSON de recomendación para el usuario {userId}: {e}")
            elif is_recommendation:
                logger.warning(f"Recomendación detectada sin marcador JSON para {userId}. Intentando extraer destinationId...")
                try:
                    destino_match = re.search(r"\*\*Destino:\*\*\s*(.+?)(?:\n|\*\*)", full_response_content)
                    if destino_match:
                        destino_nombre = destino_match.group(1).strip()
                        logger.info(f"Destino detectado en respuesta: '{destino_nombre}'")
                        destinations = get_destinations_by_budget(user_preferences_dict.get("preferencia_precio", float('inf')))
                        matching_dest = next((d for d in destinations if d.get("name") == destino_nombre), None)
                        
                        if matching_dest:
                            recommendation_data = {
                                "userId": str(userId),
                                "destinationId": matching_dest["id"],
                                "tipo": "basado_en_preferencias",
                                "aceptada": False
                            }
                            recommendation_id = await self._user_manager.save_recommendation_to_api(
                                userId, 
                                recommendation_data, 
                                auth_token
                            )
                            
                            if recommendation_id:
                                recommendation_data["recommendation_id"] = recommendation_id
                                await self._user_manager.save_last_recommendation(userId, recommendation_data)
                                command_to_return = f"GENERAR_RECOMENDACION_JSON: {json.dumps(recommendation_data)}"
                                logger.info(f"Recomendación recuperada mediante fallback para {userId}: {recommendation_data}")
                        else:
                            logger.warning(f"No se pudo encontrar destino '{destino_nombre}' en available_destinations")
                            logger.debug(f"Destinos disponibles: {[d.get('name') for d in destinations]}")
                    else:
                        logger.warning(f"No se pudo extraer el nombre del destino de la respuesta")
                except Exception as e:
                    logger.error(f"Error en fallback de recomendación para {userId}: {e}")
            self._user_manager.save_conversation_history(userId, user_conversation_history)
            full_response_content = await self._user_manager.handle_preference_setting(
                user_data_container, full_response_content, auth_token
            )
            full_response_content = PREFERENCE_MARKERS_REGEX.sub("", full_response_content).strip()
            return {
                "response": full_response_content,
                "user_name": user_data_container.get("nombre"),
                "preference_key": None,
                "preference_value": None,
                "command": command_to_return,
            }

        self._online = False
        return {
            "response": "No se pudo procesar tu solicitud. Intenta más tarde.",
            "error": "Agotados intentos",
            "user_name": user_data_container.get("nombre"),
            "preference_key": None,
            "preference_value": None,
            "command": None,
        }

    async def _get_llm_response(self, client, messages: list[dict], retries=2) -> tuple:
        """Obtiene la respuesta del modelo de lenguaje."""
        for attempt in range(retries):
            try:
                model_options = {
                    "temperature": self._config["model"].get("temperature", 0.3),
                    "num_predict": self._config["model"].get("max_tokens", 1024),
                }
                if "top_p" in self._config["model"]:
                    model_options["top_p"] = self._config["model"]["top_p"]
                
                if "top_k" in self._config["model"]:
                    model_options["top_k"] = self._config["model"]["top_k"]
                
                if "repeat_penalty" in self._config["model"]:
                    model_options["repeat_penalty"] = self._config["model"]["repeat_penalty"]
                
                if "num_ctx" in self._config["model"]:
                    model_options["num_ctx"] = self._config["model"]["num_ctx"]

                response_stream = await client.chat(
                    model=self._config["model"]["name"],
                    messages=messages,
                    options=model_options,
                    stream=True,
                )
                full_response_content = ""
                async for chunk in response_stream:
                    if "content" in chunk["message"]:
                        full_response_content += chunk["message"]["content"]

                if not full_response_content:
                    logger.warning("Respuesta vacía de Ollama. Reintentando...")
                    continue

                return full_response_content, None

            except (ResponseError, ConnectError, Exception) as e:
                logger.error(f"Error con Ollama: {e}. Reintentando...")
                if attempt == retries - 1:
                    return None, f"Error con Ollama después de {retries} intentos: {e}"
                continue

        return None, "No se pudo generar una respuesta después de varios intentos."
