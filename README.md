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
        "temperature": 0.7,     # Control de creatividad (0.0 - 1.0)
        "num_predict": 500      # Máximo de tokens a generar
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
  "speaker": "ONLINE",
  "hotword": "ONLINE",
  "mqtt": "ONLINE",
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

### POST /stt/transcribe

Convierte voz a texto usando el módulo STT.

Cuerpo de la solicitud:

```
audio_file: UploadFile
```

Respuesta:

```json
{
  "text": "string"
}
```

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
