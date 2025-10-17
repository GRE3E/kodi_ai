import os
from fastapi import APIRouter, HTTPException, Depends
from src.api.tts_schemas import TTSTextRequest, TTSAudioResponse
import logging
from pathlib import Path
import uuid
from src.api import utils
from src.api.audio_utils import AUDIO_OUTPUT_DIR, play_audio

logger = logging.getLogger("APIRoutes")

tts_router = APIRouter()

@tts_router.post("/tts/generate_audio", response_model=TTSAudioResponse)
async def generate_audio(request: TTSTextRequest):
    """Genera un archivo de audio a partir de texto usando el módulo TTS.

    Args:
        request (TTSTextRequest): Objeto de solicitud que contiene el texto a convertir.

    Returns:
        TTSAudioResponse: Objeto de respuesta que contiene la ruta al archivo de audio generado.

    Raises:
        HTTPException: Si el módulo TTS está fuera de línea o si ocurre un error durante la generación de audio.
    """
    if utils._tts_module is None or not utils._tts_module.is_online():
        raise HTTPException(status_code=503, detail="El módulo TTS está fuera de línea")
    
    try:
        audio_filename = f"tts_audio_{uuid.uuid4()}.wav"
        file_location = AUDIO_OUTPUT_DIR / audio_filename
        
        future_audio_generated = utils._tts_module.generate_speech(request.text, str(file_location))
        audio_generated = future_audio_generated.result()

        if not audio_generated:
            raise HTTPException(status_code=500, detail="No se pudo generar el audio")
        
        response_obj = TTSAudioResponse(audio_file_path=str(file_location))
        logger.info(f"Audio TTS generado exitosamente para /tts/generate_audio: {file_location}")
        return response_obj
        
    except Exception as e:
        logger.error(f"Error en generación de audio TTS para /tts/generate_audio: {e}")
        raise HTTPException(status_code=500, detail="Error al generar el audio")