# src/transcription/whisper_transcriber.py
import whisper
import torch
from config.settings import WHISPER_MODEL, LANGUAGE
from src.audio.preprocessor import split_audio

def transcribe_audio(audio_path):
    
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model(WHISPER_MODEL, device=device)
    result = model.transcribe(audio_path, language=LANGUAGE)
    
    # Retorna los segmentos en lugar de solo el texto
    return result["segments"]

def transcribe_large_audio(file_path):
    segments = split_audio(file_path)
    full_transcription = []
    
    for segment in segments:
        try:
            segment_transcription = transcribe_audio(segment)
            full_transcription.extend(segment_transcription)  # Añadir segmentos individuales
        except Exception as e:
            print(f"Error al transcribir el segmento {segment}: {e}")

    return full_transcription  # Devuelve la lista de segmentos
