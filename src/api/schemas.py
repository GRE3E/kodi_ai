from pydantic import BaseModel

class StatusResponse(BaseModel):
    """Modelo para el estado del sistema."""
    nlp: str
    stt: str = "OFFLINE"
    tts: str = "OFFLINE"
    utils: str = "OFFLINE"