import logging
import re
import json
from fastapi import APIRouter, HTTPException, Request, Depends
from src.api.nlp_schemas import NLPQuery, NLPResponse, RecommendationsResponse, Recommendation
from src.api.schemas import StatusResponse
from src.api import utils

logger = logging.getLogger("APIRoutes")

nlp_router = APIRouter()

@nlp_router.post("/nlp/query", response_model=NLPResponse)
async def query_nlp(query: NLPQuery, request: Request):
    """Procesa una consulta NLP y devuelve la respuesta generada."""

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticación Bearer no proporcionado o inválido.")
    auth_token = auth_header.split(" ")[1]

    try:

        response = await utils._nlp_module.generate_response(
            query.prompt, 
            userId=query.userId,
            auth_token=auth_token
        )

        if response.get("error"):
            raise HTTPException(status_code=500, detail=response.get("error"))
        
        response_obj = NLPResponse(
            response=response["response"],
            preference_key=response.get("preference_key"),
            preference_value=response.get("preference_value"),
            command=response.get("command"),
            prompt_sent=query.prompt,
            user_name=response.get("user_name"),
            userId=query.userId
        )
        
        logger.info(f"Consulta NLP procesada exitosamente. Respuesta completa: {response_obj.dict()}")
        
        return response_obj
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en consulta NLP para /nlp/query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar la consulta NLP: {str(e)}")


@nlp_router.post("/nlp/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(query: NLPQuery, request: Request):
    """Devuelve exactamente 3 recomendaciones en formato JSON puro, sin texto extra."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticación Bearer no proporcionado o inválido.")
    auth_token = auth_header.split(" ")[1]

    try:
        recommendation_prompt = f"""INSTRUCCIÓN CRÍTICA: Genera EXACTAMENTE 3 recomendaciones de destinos diferentes.

        FORMATO OBLIGATORIO para cada una (sin excepciones):
        **Destino:** [nombre del destino]
        **Ubicación:** [ubicación]
        **Descripción:** [breve descripción]
        **Presupuesto:** [precio] euros
        **Ideal para:** [razón según perfil del usuario]
        ---
        GENERAR_RECOMENDACION_JSON: {{"userId":"{query.userId}","destinationId":"[ID exacto del destino]","tipo":"basado_en_preferencias","aceptada":false}}

        [LÍNEA EN BLANCO]

        [Repetir para destino 2]

        [LÍNEA EN BLANCO]

        [Repetir para destino 3]

        REGLAS ABSOLUTAS:
        - USA el userId UUID: {query.userId}
        - NO uses bloques de código ```json```
        - NO generes listas de más de 3 destinos
        - El destinationId debe existir en available_destinations
        - DEBES incluir el marcador GENERAR_RECOMENDACION_JSON: para cada recomendación

        Pregunta del usuario: {query.prompt}"""
        
        response = await utils._nlp_module.generate_response(
            recommendation_prompt,
            userId=query.userId,
            auth_token=auth_token
        )
        
        raw_content = response.get("command", "")
        
        if not raw_content:
            from src.ai.nlp.user_manager import UserManager
            user_manager = UserManager()
            history = user_manager.load_conversation_history(query.userId)
            if history and len(history) > 0:
                for msg in reversed(history):
                    if msg.get("role") == "assistant":
                        raw_content = msg.get("content", "")
                        break
        
        logger.info(f"Contenido crudo para extraer recomendaciones: {raw_content[:500]}...")
        
        recomendaciones = []
        
        pattern = re.compile(
            r'(?:GENERAR_RECOMENDACION_JSON|Generar_recomendacion_JSON):\s*(\{[^}]+\})|```json\s*(\{[^}]+\})\s*```|(?:^|\n)(\{\s*"userId"[^}]+\})',
            re.DOTALL | re.IGNORECASE | re.MULTILINE
        )
        
        matches = pattern.finditer(raw_content)
        
        logger.info(f"Iniciando extracción de recomendaciones...")
        
        for match in matches:
            json_str = match.group(1) or match.group(2) or match.group(3)
            if not json_str:
                continue
            
            json_str = json_str.strip()
            
            logger.debug(f"JSON extraído: {json_str}")
            
            try:
                rec = json.loads(json_str)
                
                if not all(key in rec for key in ["destinationId", "userId", "tipo", "aceptada"]):
                    logger.warning(f"JSON no tiene todas las claves necesarias: {rec}")
                    continue
                
                if rec["userId"] != query.userId:
                    logger.warning(f"Corrigiendo userId de '{rec['userId']}' a '{query.userId}'")
                    rec["userId"] = query.userId
                
                if any(r.destinationId == rec["destinationId"] for r in recomendaciones):
                    logger.info(f"Destino duplicado ignorado: {rec['destinationId']}")
                    continue
                
                from src.ai.nlp.user_manager import UserManager
                user_manager = UserManager()
                recommendation_id = await user_manager.save_recommendation_to_api(
                    query.userId,
                    rec,
                    auth_token
                )
                
                if recommendation_id:
                    rec["recommendation_id"] = recommendation_id
                    recomendaciones.append(Recommendation(**rec))
                    logger.info(f"Recomendación {len(recomendaciones)} procesada y guardada con ID {recommendation_id}: {rec['destinationId']}")
                else:
                    logger.warning(f"No se pudo guardar la recomendación en la API, pero se agregará a la respuesta")
                    recomendaciones.append(Recommendation(**rec))
                
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear JSON: {e} - Contenido: {json_str[:200]}")
                continue
            except Exception as e:
                logger.error(f"Error al procesar recomendación: {e}", exc_info=True)
                continue
            
            if len(recomendaciones) >= 3:
                logger.info("Se alcanzaron 3 recomendaciones, deteniendo búsqueda")
                break
        
        logger.info(f"Total de recomendaciones extraídas: {len(recomendaciones)}")

        if len(recomendaciones) < 3:
            logger.warning(f"Solo se generaron {len(recomendaciones)} recomendaciones, intentando obtener más...")
            try:
                additional_prompt = f"""CRÍTICO: Necesito EXACTAMENTE {3 - len(recomendaciones)} recomendaciones MÁS.

                FORMATO OBLIGATORIO (copia este formato exactamente):
                **Destino:** [nombre]
                **Ubicación:** [ubicación]
                **Descripción:** [descripción]
                **Presupuesto:** [precio] euros
                ---
                GENERAR_RECOMENDACION_JSON: {{"userId":"{query.userId}","destinationId":"[id]","tipo":"basado_en_categoria","aceptada":false}}  

                NO repitas estos destinos: {[r.destinationId for r in recomendaciones]}
                USA diferentes destinos de available_destinations."""

                additional_response = await utils._nlp_module.generate_response(
                    additional_prompt,
                    userId=query.userId,
                    auth_token=auth_token
                )
                
                additional_raw = additional_response.get("command", "")
                if not additional_raw:
                    from src.ai.nlp.user_manager import UserManager
                    user_manager = UserManager()
                    history = user_manager.load_conversation_history(query.userId)
                    if history and len(history) > 0:
                        for msg in reversed(history):
                            if msg.get("role") == "assistant":
                                additional_raw = msg.get("content", "")
                                break
                
                additional_matches = pattern.finditer(additional_raw)
                logger.info(f"Buscando recomendaciones adicionales...")
                
                for match in additional_matches:
                    json_str = match.group(1) or match.group(2) or match.group(3)
                    if not json_str:
                        continue
                    
                    json_str = json_str.strip()
                    
                    try:
                        rec = json.loads(json_str)
                        if not all(key in rec for key in ["destinationId", "userId", "tipo", "aceptada"]):
                            continue
                        
                        if rec["userId"] != query.userId:
                            rec["userId"] = query.userId
                        
                        if any(r.destinationId == rec["destinationId"] for r in recomendaciones):
                            continue
                        
                        from src.ai.nlp.user_manager import UserManager
                        user_manager = UserManager()
                        recommendation_id = await user_manager.save_recommendation_to_api(
                            query.userId,
                            rec,
                            auth_token
                        )
                        
                        if recommendation_id:
                            rec["recommendation_id"] = recommendation_id
                        
                        recomendaciones.append(Recommendation(**rec))
                        logger.info(f"Recomendación adicional procesada: {rec['destinationId']}")
                        
                    except Exception:
                        continue
                    
                    if len(recomendaciones) >= 3:
                        break
                        
            except Exception as e:
                logger.error(f"Error al obtener recomendaciones adicionales: {e}", exc_info=True)

        if len(recomendaciones) > 0 and len(recomendaciones) < 3:
            logger.warning(f"Solo se pudieron generar {len(recomendaciones)} recomendaciones únicas")
            while len(recomendaciones) < 3:
                last_rec = recomendaciones[-1]
                recomendaciones.append(last_rec)
        
        if len(recomendaciones) == 0:
            raise HTTPException(
                status_code=500,
                detail="No se pudieron generar recomendaciones. El modelo no generó el formato esperado. Por favor, intenta con un prompt más específico o verifica que haya destinos disponibles."
            )
        
        recomendaciones = recomendaciones[:3]
        logger.info(f"Devolviendo {len(recomendaciones)} recomendaciones finales")
        return {"recommendations": recomendaciones}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en consulta NLP para /nlp/recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar las recomendaciones: {str(e)}")