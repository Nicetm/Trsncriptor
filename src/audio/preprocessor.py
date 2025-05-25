import os
import subprocess

def preprocess_audio(video_path):
    """
    Convierte un archivo de video a formato de audio WAV robusto.
    
    :param video_path: Ruta del archivo de video.
    :return: Ruta del archivo de audio en formato WAV.
    """
    base_name = os.path.splitext(video_path)[0]
    wav_output_path = f"{base_name}.wav"
    
    command = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn",  # Ignorar video
        "-ac", "1",  # Forzar audio mono
        "-ar", "16000",  # Establecer tasa de muestreo
        "-sample_fmt", "s16",  # Asegurar formato de muestra
        wav_output_path
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return wav_output_path
    except subprocess.CalledProcessError as e:
        print(f"Error en la conversión a WAV: {e.stderr}")
        return None



def split_audio(audio_path, segment_duration=1800):
    """
    Divide un archivo de audio en segmentos robustos.
    
    :param audio_path: Ruta del archivo de audio original (en formato WAV).
    :param segment_duration: Duración de cada segmento en segundos (por defecto, 30 minutos).
    :return: Lista de rutas de los segmentos generados.
    """
    base_name = os.path.splitext(audio_path)[0]
    output_dir = f"{base_name}_segments"
    os.makedirs(output_dir, exist_ok=True)

    command = [
        "ffmpeg", "-i", audio_path,
        "-f", "segment",
        "-segment_time", str(segment_duration),
        "-c", "pcm_s16le",  # Usar un formato robusto
        os.path.join(output_dir, "segment_%03d.wav")
    ]

    try:
        subprocess.run(command, check=True, text=True)
        segment_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".wav")]
        return segment_files
    except subprocess.CalledProcessError as e:
        print(f"Error al dividir el audio: {e.stderr}")
        return []

