import logging
import wave
from pathlib import Path
import pyaudio

logger = logging.getLogger("AudioUtils")

# Directorio para guardar los audios generados
AUDIO_OUTPUT_DIR = Path("src/ai/tts/generated_audio")
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def play_audio(file_path: str):
    """
    Reproduce un archivo de audio WAV.
    """
    try:
        wf = wave.open(file_path, 'rb')
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
        logger.info(f"Audio reproducido exitosamente: {file_path}")
    except Exception as e:
        logger.error(f"Error al reproducir audio {file_path}: {e}")