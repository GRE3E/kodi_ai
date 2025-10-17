import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Optional
from src.api.schemas import StatusResponse
from .tts_routes import tts_router
from src.api.nlp_routes import nlp_router
from src.api.stt_routes import stt_router

from src.api import utils

logger = logging.getLogger("APIRoutes")

router = APIRouter()

router.include_router(tts_router, prefix="/tts", tags=["tts"])
router.include_router(nlp_router, prefix="/nlp", tags=["nlp"])
router.include_router(stt_router, prefix="/stt", tags=["stt"])

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Devuelve el estado actual de los módulos."""
    try:
        status: StatusResponse = utils.get_module_status()
        logger.info(f"Status Response para /status: {status.model_dump_json()}")
        return status
    except Exception as e:
        logger.error(f"Error al obtener estado para /status: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")   