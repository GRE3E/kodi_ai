import logging
import re
from fastapi import APIRouter, HTTPException, Request, Depends
from src.api.nlp_schemas import NLPQuery, NLPResponse
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