# Proyecto AI - Asistente para ayudar al turista

## Descripción

Es un asistente virtual diseñado para ayudar a los turistas a planificar sus viajes, obtener información sobre lugares turísticos, y proporcionar recomendaciones personalizadas. Utiliza procesamiento de lenguaje natural (NLP), reconocimiento de voz (STT y Speaker Recognition), síntesis de voz (TTS), detección de hotword y comunicación con dispositivos IoT a través de MQTT.

## Requisitos (actualizar)

- Python 3.10 o superior
- Ollama instalado con el modelo (para NLP)
- Dependencias listadas en `requirements.txt`
- Modelos de Whisper (se descargarán automáticamente al usar el módulo STT)

## Instalación

1.  **Crear y activar entorno virtual:**

    ```powershell
    python -m venv .venv
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process; ./.venv/Scripts/Activate.ps1
    ```

2.  **Instalar dependencias:**

    ```powershell
    pip install -r requirements.txt
    ```

3.  **Instalar PyTorch con soporte para CUDA (si se dispone de GPU NVIDIA):**
    Asegúrate de tener el CUDA Toolkit de NVIDIA instalado en tu sistema. Luego, instala PyTorch con el siguiente comando (ajusta `cu121` a la versión de CUDA que tengas instalada, por ejemplo, `cu118` para CUDA 11.8):

    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process; ./.venv/Scripts/Activate.ps1; pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```

4.  **Asegurarse de tener Ollama instalado y el modelo descargado (para NLP):**

    ```powershell
    ollama list  # Verificar que el modelo está instalado
    ```

5.  **El sistema utiliza la variable de entorno OLLAMA_OPTIONS para configurar los parámetros del modelo de NLP:**

        ```json
        {
        "assistant_name": "KODI",
        "language": "es",
        "model": {
            "name": "qwen2.5:3b-instruct",
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_ctx": 8192,
            "max_tokens": 1024
        },
        "timezone": "America/Bogota"
        }

        ```

## Uso

1.  **Iniciar el servidor:**

    ```powershell
    uvicorn src.main:app --reload
    ```

    **Nota:** El servidor de Ollama se iniciará automáticamente en segundo plano cuando la aplicación se inicie. No es necesario ejecutar `ollama serve` manualmente.

2.  **El servidor estará disponible en:**

    - API: `http://127.0.0.1:8000`
    - Documentación: `http://127.0.0.1:8000/docs`

## Endpoints

Los endpoints de la API están definidos en el directorio `src/api/` y se agrupan por funcionalidad. Puedes explorar la documentación interactiva en `http://127.0.0.1:8000/docs` para ver todos los endpoints disponibles y sus esquemas.

### GET /status

Verifica el estado actual de los módulos.

Respuesta:

```json
{
  "nlp": "ONLINE",
  "stt": "ONLINE",
  "tts": "ONLINE",
  "utils": "ONLINE"
}
```

### POST /tts/generate_audio

Genera un archivo de audio a partir de texto usando el módulo TTS.

Cuerpo de la solicitud:

```json
{
  "text": "string"
}
```

Respuesta:

```json
{
  "audio_file_path": "string"
}
```

### POST /nlp/query

Procesa una consulta NLP y devuelve la respuesta generada.
**Headers requeridos:**Authorization: Bearer {token}
Cuerpo de la solicitud:

```json
{
  "prompt": "string",
  "userId": "string"
}
```

Respuesta:

```json
{
  "prompt_sent": "string",
  "response": "string",
  "command": "string",
  "user_name": "string",
  "userId": "string"
}
```

### POST /nlp/recommendations

Genera exactamente 3 recomendaciones de destinos turísticos basadas en las preferencias del usuario y las guarda automáticamente en la base de datos.
**Headers requeridos:**Authorization: Bearer {token}
**Cuerpo de la solicitud:**

````json
{
"prompt": "string",
"userId": "string"
}

**Ejemplo de solicitud:**

```json{
"prompt": "¿Qué destinos me recomiendas para vacaciones?",
"userId": "1c9d0149-1288-42dc-931f-27cab21fbc46"
}

**Respuesta exitosa (200 OK):**

```json{
"recommendations": [
    {
      "destinationId": "9d218366-546b-4253-bb99-304ab116cf78",
      "userId": "1c9d0149-1288-42dc-931f-27cab21fbc46",
      "tipo": "basado_en_preferencias",
      "aceptada": false
    },
    {
      "destinationId": "c7407f83-3923-4623-9363-3e5e67ea83e9",
      "userId": "1c9d0149-1288-42dc-931f-27cab21fbc46",
      "tipo": "basado_en_presupuesto",
      "aceptada": false
    },
    {
      "destinationId": "b7349b99-8d5b-4068-ae50-f50f731d4f1d",
      "userId": "1c9d0149-1288-42dc-931f-27cab21fbc46",
      "tipo": "basado_en_categoria",
      "aceptada": false
    }
  ]
}

### POST /stt/transcribe

Convierte voz a texto usando el módulo STT.

Cuerpo de la solicitud:

````

audio_file: UploadFile

````

Respuesta:

```json
{
  "text": "string"
}
````

## Estructura del Proyecto

```
.
├── .gitignore
├── .venv/
├── data/
│   └── 4841d633-34a4-4ba8-90d2-d3b72090b5f6_history.json
├── requirements.txt
├── README.md
└── src/
    ├── ai/
    │   ├── __init__.py
    │   ├── config/
    │   ├── nlp/
    │   ├── stt/
    │   ├── tts/
    │   └── utils/
    ├── api/
    │   ├── __init__.py
    │   ├── audio_utils.py
    │   ├── nlp_routes.py
    │   ├── nlp_schemas.py
    │   ├── routes.py
    │   ├── schemas.py
    │   ├── stt_routes.py
    │   ├── stt_schemas.py
    │   ├── tts_routes.py
    │   ├── tts_schemas.py
    │   └── utils.py
    ├── main.py
    ├── test/
    │   └── test_ai_chatbot.py
    └── utils/
        ├── __init__.py
        ├── datetime_utils.py
        ├── destination_api.py
        ├── error_handler.py
        └── logger_config.py
```
