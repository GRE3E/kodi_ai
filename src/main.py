import os
import asyncio
import logging
import warnings
from typing import Dict, Any, Optional
from src.utils.error_handler import ErrorHandler

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
# IMPORTANTE: Configurar la política del bucle de eventos ANTES de cualquier otra importación
if os.name == 'nt':  # Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from src.api.routes import router
from src.api.utils import initialize_all_modules
from src.api import utils
import httpx
import json
import pyaudio
import wave
from datetime import datetime
import numpy as np
from src.utils.logger_config import setup_logging

setup_logging()
logger = logging.getLogger("MainApp")

app = FastAPI(title="Casa Inteligente API")

CONFIG_PATH = "src/ai/config/config.json"

@ErrorHandler.handle_exceptions
def load_config() -> Dict[str, Any]:
    """
    Carga la configuración desde config.json o crea una por defecto si no existe.

    Returns:
        Dict[str, Any]: Diccionario con la configuración cargada o por defecto.
    """
    default_config = {
            "assistant_name": "KODI",
            "language": "es",
            "model": {
            "name": "qwen2.5:3b-instruct",
            "temperature": 0.7,
            "max_tokens": 200,
            }
        }
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Archivo de configuración no encontrado en {CONFIG_PATH}. Creando configuración por defecto.")
        config = default_config
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar JSON en {CONFIG_PATH}: {e}. Usando configuración por defecto.")
        config = default_config
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    return config

@app.on_event("startup")
@ErrorHandler.handle_async_exceptions
async def startup_event() -> None:
    """
    Evento de inicio de la aplicación.
    Inicializa la configuración, la base de datos y los módulos de IA/IoT.
    """
    logger.info("Iniciando aplicación Casa Inteligente...")
    
    config = load_config()
    logger.info(f"Configuración cargada: {config}")
    
    await initialize_all_modules()
    logger.info("Aplicación iniciada correctamente")

@app.on_event("shutdown")
@ErrorHandler.handle_async_exceptions
async def shutdown_event() -> None:
    """
    Evento de cierre de la aplicación.
    """
    logger.info("Cerrando aplicación...")
    logger.info("Aplicación cerrada correctamente")

app.include_router(router, prefix="")