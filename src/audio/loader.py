# src/audio/loader.py
import os
from pydub import AudioSegment

def load_audio(audio_path):
    if not os.path.exists(audio_path):
        raise FileNotFoundError("Archivo de audio no encontrado")
    audio = AudioSegment.from_file(audio_path)
    return audio
