import gradio as gr
from gradio_modal import Modal
import os
import torch
import socket
import time
import webbrowser
import requests
import json
from datetime import datetime
from flask import Flask, session
from multiprocessing import Process
from pyannote.audio import Pipeline
from utils.file_handler import save_as_text, save_as_docx, save_as_pdf
from src.transcription.whisper_transcriber import transcribe_audio
from src.audio.preprocessor import split_audio
from src.auth.google_auth import app as flask_app
from pathlib import Path

# Variable global para almacenar el estado de usuario autenticado
authenticated_user = None
# Lista global para rastrear los archivos ya cargados
# Diccionario global para el registro
file_registry = {}

# Función para cargar los datos existentes en la tabla
def load_existing_data():
    global file_registry

    # Asegurarse de que el registro esté inicializado
    initialize_file_registry()

    # Construir la tabla con TODOS los registros
    result_data = []
    for file_name, data in file_registry.items():
        result_data.append([file_name, data["status"], data["time"], data["download_link"]])

    return format_markdown_table(result_data)


# Función para inicializar el registro desde un archivo JSON
def initialize_file_registry():
    try:
        with open("file_registry.json", "r") as f:
            file_registry = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        file_registry = {}

# Función para guardar el registro en un archivo JSON
def save_file_registry():
    global file_registry
    with open("file_registry.json", "w") as f:
        json.dump(file_registry, f, indent=4)


import atexit
atexit.register(save_file_registry)
initialize_file_registry()

# Función para cargar los archivos y mostrarlos en la tabla
def load_files(files):
    global file_registry

    # Leer el archivo JSON al cargar
    initialize_file_registry()

    # Añadir nuevos archivos al registro
    for file in files:
        file_name = os.path.basename(file.name)
        if file_name not in file_registry:
            # Agregar el nuevo archivo al registro
            file_registry[file_name] = {
                "status": "Pendiente",
                "time": "-",
                "download_link": ""
            }

    # Guardar el registro actualizado
    save_file_registry()

    # Construir la tabla con TODOS los registros del registro global
    return load_existing_data()


def format_status(status):
    status_map = {
        "Pendiente": '<span style="color: orange; font-weight: bold;">Pendiente</span>',
        "Procesando...": '<span style="color: blue; font-weight: bold;">Procesando...</span>',
        "Finalizado": '<span style="color: green; font-weight: bold;">Finalizado</span>',
        "Error": '<span style="color: red; font-weight: bold;">Error</span>',
    }
    return status_map.get(status, status)  # Devuelve el estilo correspondiente

# Función para formatear los datos en Markdown
def format_markdown_table(data):
    markdown_text = "| Nombre | Estado | Tiempo (s) | Descargar |\n| --- | --- | --- | --- |\n"
    for row in data:
        try:
            status_styled = format_status(row[1])
            markdown_text += f"| {row[0]} | {status_styled} | {row[2]} | {row[3]} |\n"
        except Exception as e:
            # Captura cualquier problema con los datos
            print(f"Error al procesar la fila: {row}. Error: {e}")
    return markdown_text

def wait_for_flask(host="127.0.0.1", port=5000, timeout=30):
    """Espera a que Flask esté escuchando en el puerto antes de proceder."""
    start_time = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"Flask está listo en https://{host}:{port}")
                return
        except (socket.timeout, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"No se pudo conectar a Flask en https://{host}:{port} después de {timeout} segundos.")
            print("Esperando a que Flask esté listo...")
            time.sleep(1)

def run_flask():
    try:
        flask_app.run(host="127.0.0.1", port=5000, ssl_context=("cert/cert.pem", "cert/key.pem"))
    except Exception as e:
        print(f"Error al iniciar Flask: {e}")

def update_user_status():
    max_retries = 2
    retry_delay = 2  # Segundos entre reintentos

    for attempt in range(max_retries):
        try:
            # Realiza una solicitud al endpoint de Flask para verificar el usuario
            response = requests.get("https://127.0.0.1:5000/get_user", verify=False)  # Desactiva SSL en local
            data = response.json()

            if "error" not in data:
                return f"Autenticado como {data['name']} ({data['email']})"
            return "No autenticado"
        except requests.ConnectionError as e:
            time.sleep(retry_delay)
        except Exception as e:
            return f"Error inesperado al conectar con Flask: {e}"

    return "No se pudo conectar con Flask después de varios intentos."

# Función para transcribir los archivos con actualizaciones en tiempo real
def transcribe_files(files, file_format):
    global file_registry

    # Validar que se hayan subido archivos
    if not files or len(files) == 0:
        yield "No se han seleccionado archivos para transcribir.", ""

    # Leer el estado actual de los archivos
    initialize_file_registry()

    # Inicializar la tabla con el estado "Pendiente" solo para los archivos nuevos
    result_data = []
    for file in files:
        file_path = file.name
        file_name = os.path.basename(file_path)

        if file_name not in file_registry:
            # Agregar nuevos archivos al registro global
            file_registry[file_name] = {"status": "Pendiente", "time": "-", "download_link": ""}
            result_data.append([file_name, "Pendiente", "-", ""])
        else:
            # Recuperar el estado de los archivos ya existentes
            data = file_registry[file_name]
            result_data.append([file_name, data["status"], data["time"], data["download_link"]])

    # Guardar el estado actualizado en el archivo JSON
    save_file_registry()

    yield format_markdown_table(result_data), ""  # Mostrar el estado inicial de la tabla

    for idx, file in enumerate(files):
        file_path = file.name
        file_name = os.path.basename(file_path)

        if file_registry[file_name]["status"] != "Pendiente":
            # Saltar archivos ya procesados
            continue

        # Marcar el archivo como "Procesando..."
        result_data[idx][1] = "Procesando..."
        file_registry[file_name]["status"] = "Procesando..."
        yield format_markdown_table(result_data), ""  # Mostrar el cambio a "Procesando..."
        save_file_registry()  # Guardar el estado actualizado
        time.sleep(3)

        start_time = datetime.now()

        try:
            # Dividir audio en fragmentos
            result_data[idx][1] = "Fragmentando..."
            file_registry[file_name]["status"] = "Fragmentando..."
            yield format_markdown_table(result_data), ""
            save_file_registry()

            segment_paths = split_audio(file_path)
            time.sleep(3)

            # Transcribir fragmentos y combinarlos
            full_transcription = ""
            total_segments = len(segment_paths)  # Obtener el total de segmentos para calcular el porcentaje
            torch_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            result_data[idx][1] = "Transcribiendo... (0%)"
            file_registry[file_name]["status"] = "Transcribiendo... (0%)"
            yield format_markdown_table(result_data), ""
            save_file_registry()

            transcription_with_timestamps = []

            for i, segment in enumerate(segment_paths):
                progress = int((i + 1) / len(segment_paths) * 100)
                result_data[idx][1] = f"Transcribiendo... ({progress}%)"
                file_registry[file_name]["status"] = f"Transcribiendo... ({progress}%)"
                yield format_markdown_table(result_data), ""
                save_file_registry()

                transcription_segments = transcribe_audio(segment)  # Obtiene los segmentos con tiempos
                for seg in transcription_segments:
                    transcription_with_timestamps.append({
                        "start": seg["start"],  # Tiempo de inicio del segmento
                        "end": seg["end"],      # Tiempo de fin del segmento
                        "text": seg["text"]     # Texto del segmento
                    })
                time.sleep(3)

            # Generar la transcripción completa para el PDF
            full_transcription = "\n".join([seg["text"] for seg in transcription_with_timestamps])

            # Actualizar el porcentaje de progreso
            progress = int((i + 1) / total_segments * 100)
            result_data[idx][1] = f"Transcribiendo... ({progress}%)"
            file_registry[file_name]["status"] = f"Transcribiendo... ({progress}%)"
            yield format_markdown_table(result_data), ""
            save_file_registry()

            # Guardar resultado en formato seleccionado
            output_filename = f"{os.path.splitext(file_name)[0]}.{file_format.lower()}"
            output_path = os.path.join(os.path.dirname(file_path), output_filename)

            result_data[idx][1] = "Generando documento..."
            file_registry[file_name]["status"] = "Generando documento..."
            yield format_markdown_table(result_data), ""
            save_file_registry()

            if file_format == "TXT":
                save_as_text(full_transcription, output_path)
            elif file_format == "DOCX":
                save_as_docx(full_transcription, output_path)
            elif file_format == "PDF":
                save_as_pdf(full_transcription, output_path)
            time.sleep(3)

            end_time = datetime.now()
            elapsed_time = round((end_time - start_time).total_seconds(), 2)

            # Generar URL del archivo para descarga
            # document_url = f"/gradio_api/file={output_path.replace('\\', '/')}"
            document_url = f"/gradio_api/file={Path(output_path).as_posix()}"

            download_link = f"<a href='{document_url}' download='{output_filename}'>Descargar ⇣</a>"

            # Actualizar datos en la tabla con el enlace de descarga
            result_data[idx] = [
                file_name,
                "Finalizado",
                elapsed_time,
                download_link
            ]
            file_registry[file_name] = {
                "status": "Finalizado",
                "time": elapsed_time,
                "download_link": download_link
            }
            yield format_markdown_table(result_data), ""  # Actualizar la tabla después de procesar cada archivo
            save_file_registry()

        except Exception as e:
            result_data[idx] = [
                file_name,
                f"Error: {e}",
                "-",
                ""
            ]
            file_registry[file_name]["status"] = f"Error: {e}"
            save_file_registry()
            yield format_markdown_table(result_data), ""  # Mostrar error en la tabla si ocurre una excepción

    # Estado final de la tabla
    yield format_markdown_table(result_data), ""

# Interfaz con Gradio
with gr.Blocks() as demo:
    with gr.Sidebar():
        gr.Markdown("### Menú")
        auth_button = gr.Button("Iniciar sesión con Google", size="sm")
        logout_button = gr.Button("Cerrar sesión", size="sm")
        user_status = gr.Textbox(label="Estado del usuario", interactive=False)

    gr.Markdown("## Transcriptor de Audio a Texto")

    # Actualiza el estado del usuario
    user_status.value = update_user_status()

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Archivos")
            audio_input = gr.File(file_count="multiple", label="Seleccionar archivos de audio")
            with gr.Blocks():
                format_selector = gr.Dropdown(choices=["TXT", "DOCX", "PDF"], label="Seleccionar formato de archivo", value="PDF")
            load_button = gr.Button("Cargar Archivos", interactive=True)

        with gr.Column(scale=3):
            gr.Markdown("### Resultados")
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Row():
                        with gr.Column(scale=4):
                            gr.Row(visible=False)
                        with gr.Column(scale=1):
                            show_btn = gr.Button("Ver Detalle")
                        with gr.Column(scale=1):
                            transcribe_button = gr.Button("Transcribir", interactive=True, scale=1, min_width=300)

            #result_output = gr.Markdown(value="| Nombre | Estado | Tiempo (s) | Descargar |\n| --- | --- | --- | --- |\n", elem_id="result_table", elem_classes="table")  # Usando Markdown para mostrar la tabla y asignando un ID
            result_output = gr.Markdown(
                value=load_existing_data(),  # Mostrar los datos al iniciar
                elem_id="result_table",
                elem_classes="table"
            )            
        
        with Modal(visible=False, elem_classes="modal-status") as modal:
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Detalle Proceso")
                    modal_output = gr.Textbox(show_label=False)

    # Estilos personalizados para que la tabla ocupe el 100% del ancho
    demo.css = """
        #result_table {
        width: 100%;
        overflow-x: auto;
        font-family: Arial, sans-serif;
        border-collapse: collapse;
    }
    .modal-status .modal-block {
        width: 20%;
        float: right;
    }
    #result_table table {
        width: 100%;
        table-layout: fixed;
    }
    #result_table table a {
        text-decoration: none !important;
    }
    #result_table th {
        background-color: #333;
        color: #FFF;
        padding: 12px;
        text-align: center;
        border: 1px solid var(--block-border-color) !important;
    }
    #result_table th:first-child {
        width: 50%;
    }
    #result_table td {
        padding: 10px;
        border: 1px solid var(--block-border-color) !important;
        text-align: center; /* Centrar contenido */
    }
    #result_table td:nth-child(1) {
        text-align: left; /* Alinear texto de la primera columna */
        width: 50%;
    }
    #result_table tr:nth-child(even) {
        background-color: #2e2e2e;
    }
    #result_table tr:nth-child(odd) {
        background-color: #1e1e1e;
    }
    #result_table tr:hover {
        background-color: #444;
        cursor: pointer;
    }
    """

    # Configuración de botones
    show_btn.click(lambda: Modal(visible=True), None, modal)

    load_button.click(
        load_files,  # Llama a `load_files` para cargar nuevos archivos
        inputs=audio_input,
        outputs=result_output,  # Actualiza la tabla con TODOS los datos
        show_progress=False
    )

    auth_button.click(
        lambda: (webbrowser.open("https://127.0.0.1:5000/login"), update_user_status())[1],  # Abre el navegador y actualiza estado
        inputs=None,
        outputs=user_status  # Muestra el estado actualizado en la interfaz
    )

    logout_button.click(
        lambda: (webbrowser.open("https://127.0.0.1:5000/logout"), update_user_status())[1],  # Abre el navegador y actualiza estado
        inputs=None,
        outputs=user_status  # Muestra el estado actualizado en la interfaz
    )

    transcribe_button.click(
        transcribe_files,
        inputs=[audio_input, format_selector],
        outputs=[result_output, modal_output]
    )

if __name__ == "__main__":
    flask_process = Process(target=run_flask)
    flask_process.start()
    # Esperar a que Flask esté disponible
    time.sleep(5)
    demo.launch(share=True)
