from src.ai.nlp.nlp_core import NLPModule
from src.ai.stt.stt import STTModule
from src.ai.tts.tts_module import TTSModule
import os
import logging
from datetime import datetime
import json

import asyncio
from src.api.schemas import StatusResponse
from typing import Optional, Dict, Any
from src.utils.error_handler import ErrorHandler

logger = logging.getLogger("APIUtils")

_nlp_module: Optional[NLPModule] = None
_stt_module: Optional[STTModule] = None
_tts_module: Optional[TTSModule] = None

def get_module_status() -> StatusResponse:
    """
    Devuelve el estado actual de los módulos.

    Returns:
        StatusResponse: Objeto con el estado de cada módulo (ONLINE/OFFLINE).
    """
    nlp_status = "ONLINE" if _nlp_module and _nlp_module.is_online() else "OFFLINE"
    stt_status = "ONLINE" if _stt_module and _stt_module.is_online() else "OFFLINE"
    tts_status = "ONLINE" if _tts_module and _tts_module.is_online() else "OFFLINE"
    utils_status = "ONLINE" if _nlp_module else "OFFLINE"
    
    return StatusResponse(
        nlp=nlp_status,
        stt=stt_status,
        tts=tts_status,
        utils=utils_status
    )

def _sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    sensitive_keys = ["password", "token", "access_key", "secret", "api_key"]
    sanitized_data = data.copy()
    for key in sensitive_keys:
        if key in sanitized_data:
            sanitized_data[key] = "[REDACTED]"
    return sanitized_data

@ErrorHandler.handle_async_exceptions
async def initialize_nlp_module() -> None:
    """
    Inicializa el módulo NLP.
    """
    global _nlp_module
    logger.info("Inicializando módulo NLP...")
    _nlp_module = await ErrorHandler.safe_execute_async(
        lambda: NLPModule(),
        default_return=None,
        context="initialize_nlp.nlp_module"
    )
    logger.info(f"NLPModule inicializado. Online: {_nlp_module.is_online() if _nlp_module else False}")

@ErrorHandler.handle_async_exceptions
async def initialize_stt_module() -> None:
    """
    Inicializa el módulo STT.
    """
    global _stt_module
    logger.info("Inicializando módulo STT...")
    _stt_module = await ErrorHandler.safe_execute_async(
        lambda: STTModule(),
        default_return=None,
        context="initialize_nlp.stt_module"
    )
    logger.info(f"STTModule inicializado. Online: {_stt_module.is_online() if _stt_module else False}")

@ErrorHandler.handle_async_exceptions
async def initialize_tts_module() -> None:
    """
    Inicializa el módulo TTS.
    """
    global _tts_module
    logger.info("Inicializando módulo TTS...")
    _tts_module = await ErrorHandler.safe_execute_async(
        lambda: TTSModule(),
        default_return=None,
        context="initialize_nlp.tts_module"
    )
    logger.info(f"TTSModule inicializado. Online: {_tts_module.is_online() if _tts_module else False}")

async def initialize_all_modules() -> None:
    """
    Inicializa todos los módulos (NLP, STT, TTS).
    """
    logger.info("Inicializando todos los módulos...")
    await initialize_nlp_module()
    await initialize_stt_module()
    await initialize_tts_module()
    logger.info("Todos los módulos inicializados correctamente.")