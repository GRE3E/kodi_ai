from pydantic import BaseModel, field_validator
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

class Recommendation(BaseModel):
    """Modelo para una recomendación individual."""
    destinationId: str
    userId: str
    tipo: str
    aceptada: bool

class RecommendationsResponse(BaseModel):
    """Modelo para la respuesta de recomendaciones (exactamente 3)."""
    recommendations: list[Recommendation]

    @field_validator('recommendations')
    @classmethod
    def validate_recommendations_count(cls, v):
        if len(v) != 3:
            raise ValueError('Se requieren exactamente 3 recomendaciones')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "recommendations": [
                    {
                        "destinationId": "id1",
                        "userId": "user1",
                        "tipo": "basado_en_preferencias",
                        "aceptada": False
                    },
                    {
                        "destinationId": "id2",
                        "userId": "user1",
                        "tipo": "basado_en_presupuesto",
                        "aceptada": False
                    },
                    {
                        "destinationId": "id3",
                        "userId": "user1",
                        "tipo": "basado_en_categoria",
                        "aceptada": False
                    }
                ]
            }
        }