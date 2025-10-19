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
    """Devuelve hasta 3 recomendaciones en formato JSON puro, sin texto extra."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticación Bearer no proporcionado o inválido.")
    auth_token = auth_header.split(" ")[1]

    try:
        recommendation_prompt = f"{query.prompt}. OBLIGATORIAMENTE genera EXACTAMENTE 3 recomendaciones diferentes. EN BASE A MIS DATOS"
        
        response = await utils._nlp_module.generate_response(
            recommendation_prompt,
            userId=query.userId,
            auth_token=auth_token
        )
        
        raw_content = response.get("command", "")
        
        recomendaciones = []
        pattern = re.compile(r"(?:GENERAR_RECOMENDACION_JSON|Generar_recomendacion_JSON):\s*({.*?})", re.DOTALL | re.IGNORECASE)
        if not raw_content:
            from src.ai.nlp.user_manager import UserManager
            user_manager = UserManager()
            history = user_manager.load_conversation_history(query.userId)
            if history and len(history) > 0:
                for msg in reversed(history):
                    if msg.get("role") == "assistant":
                        raw_content = msg.get("content", "")
                        break
        
        logger.info(f"Contenido crudo para extraer recomendaciones: {raw_content[:200]}...")
        matches = pattern.findall(raw_content)
        
        logger.info(f"Se encontraron {len(matches)} recomendaciones en el contenido crudo")
        
        for match in matches:
            try:
                rec = json.loads(match)
                if all(key in rec for key in ["destinationId", "userId", "tipo", "aceptada"]):
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
                        logger.info(f"Recomendación procesada y guardada con ID {recommendation_id}: {rec['destinationId']}")
                    else:
                        logger.warning(f"No se pudo guardar la recomendación en la API, pero se agregará a la respuesta")
                        recomendaciones.append(Recommendation(**rec))
            except Exception as e:
                logger.error(f"Error al procesar recomendación JSON: {e}", exc_info=True)
                continue
        if len(recomendaciones) < 3:
            logger.warning(f"Solo se generaron {len(recomendaciones)} recomendaciones, intentando obtener más...")
            try:
                additional_response = await utils._nlp_module.generate_response(
                    "Dame más opciones de destinos diferentes a los anteriores",
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
                
                additional_matches = pattern.findall(additional_raw)
                logger.info(f"Se encontraron {len(additional_matches)} recomendaciones adicionales")
                
                for match in additional_matches:
                    try:
                        rec = json.loads(match)
                        if all(key in rec for key in ["destinationId", "userId", "tipo", "aceptada"]):
                            # Evitar duplicados
                            if not any(r.destinationId == rec["destinationId"] for r in recomendaciones):
                                recomendaciones.append(Recommendation(**rec))
                                logger.info(f"Recomendación adicional procesada: {rec['destinationId']}")
                    except Exception:
                        continue
                    if len(recomendaciones) >= 3:
                        break
            except Exception as e:
                logger.error(f"Error al obtener recomendaciones adicionales: {e}", exc_info=True)

        if len(recomendaciones) < 3:
            logger.warning(f"Solo se pudieron generar {len(recomendaciones)} recomendaciones")
            while len(recomendaciones) < 3 and len(recomendaciones) > 0:
                last_rec = recomendaciones[-1]
                recomendaciones.append(last_rec)
        
        if len(recomendaciones) == 0:
            raise HTTPException(
                status_code=500,
                detail="No se pudieron generar recomendaciones. Intenta con un prompt más específico."
            )
        
        recomendaciones = recomendaciones[:3]
        logger.info(f"Devolviendo {len(recomendaciones)} recomendaciones")
        return {"recommendations": recomendaciones}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en consulta NLP para /nlp/recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar las recomendaciones: {str(e)}")