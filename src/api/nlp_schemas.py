from pydantic import BaseModel
from typing import Optional

class NLPQuery(BaseModel):
    """Modelo para validar las consultas al módulo NLP."""
    prompt: str
    userId: Optional[str] = None

class NLPResponse(BaseModel):
    """Modelo para las respuestas del módulo NLP."""
    prompt_sent: Optional[str] = None
    response: str
    command: Optional[str] = None
    user_name: Optional[str] = None
    userId: Optional[str] = None