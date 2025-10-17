import re
import logging

logger = logging.getLogger("TextSplitter")

MAX_SENTENCE_LENGTH = 150

def _split_text_into_sentences(text: str) -> list[str]:
    """
    Divide un texto en una lista de frases utilizando signos de puntuación como delimitadores.
    Además, divide frases muy largas en segmentos más pequeños.
    """
    logger.debug(f"Texto original para dividir: {text[:100]}...")
    sentences = re.split(r'(\.(?![0-9]|\s*Son las )|(?<!\d):(?![\d])|!|\?|;|,|-)', text)
    result = []
    current_sentence = ""
    for part in sentences:
        if not part.strip():
            continue
        if part in ['.', ':', ',', '-', ';']:
            cleaned_sentence = current_sentence.strip().strip('"\'')
            if cleaned_sentence:
                result.append(cleaned_sentence)
            current_sentence = ""
        elif part in ['!', '?']:
            current_sentence += part
            cleaned_sentence = current_sentence.strip().strip('"\'')
            if cleaned_sentence:
                result.append(cleaned_sentence)
            current_sentence = ""
        else:
            current_sentence += part
    
    if current_sentence.strip():
        result.append(current_sentence.strip())

    logger.debug(f"Frases iniciales después de la división por puntuación: {len(result)} frases.")

    final_result = []
    for sentence in result:
        if len(sentence) > MAX_SENTENCE_LENGTH:
            logger.debug(f"Frase larga detectada (longitud: {len(sentence)}): {sentence[:50]}...")
            words = sentence.split(' ')
            current_chunk = ''
            for word in words:
                if len(current_chunk) + len(word) + 1 <= MAX_SENTENCE_LENGTH:
                    current_chunk += ('' if not current_chunk else ' ') + word
                else:
                    final_result.append(current_chunk.strip())
                    logger.debug(f"Sub-frase generada por longitud: {current_chunk.strip()[:50]}...")
                    current_chunk = word
            if current_chunk:
                final_result.append(current_chunk.strip())
                logger.debug(f"Última sub-frase generada por longitud: {current_chunk.strip()[:50]}...")
        else:
            final_result.append(sentence.strip())

    logger.debug(f"Frases finales después de la división por longitud: {len(final_result)} frases. Contenido: {final_result}")
    return [s for s in final_result if s]