# Trsncriptor

Transcriptor automático de audio con autenticación Google OAuth, interfaz web Gradio y procesamiento con Whisper y PyAnnote.

## Características

- Autenticación con cuenta Google (OAuth2) (*ver sección de problemas conocidos*)
- Carga de archivos de audio para transcripción
- Transcripción automática usando Whisper
- Diarización de hablantes con PyAnnote
- Exportación a texto, Word y PDF
- Interfaz interactiva usando Gradio + FastAPI
- Gestión de sesión con Flask-Session

## Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/Nicetm/Trsncriptor.git
cd Trsncriptor
```

2. Crea y activa un entorno virtual:

```bash
python -m venv venv
venv\Scripts\activate     # En Windows
```

3. Instala dependencias:

```bash
pip install -r requirements.txt
```

4. Crea un archivo `.env` con tus credenciales de Google:

```dotenv
GOOGLE_CLIENT_ID=tu_client_id
GOOGLE_CLIENT_SECRET=tu_client_secret
SECRET_KEY=una_clave_secreta_segura
```

> Asegúrate de **no subir tu `.env` a GitHub** ni incluir claves en archivos Python directamente.

## Uso

```bash
python main.py
```

Accede a `http://localhost:7860` para usar la interfaz web.

## Estructura del Proyecto

```
transcriber_project/
│
├── main.py
├── .env
├── requirements.txt
│
├── src/
│   ├── auth/
│   │   └── google_auth.py
│   └── transcription/
│       └── whisper_transcriber.py
│
└── utils/
    └── file_handler.py
```

## Requisitos

- Python 3.10
- CUDA 11.8 (para usar Torch con GPU)
- Acceso a credenciales de Google OAuth 2.0

---

## Problemas conocidos y advertencias

- **Autenticación Google OAuth2 no estable:** La sesión no se mantiene correctamente o falla al obtener `user_info`. Se debe revisar el flujo y lectura desde `.env`.
- **Advertencia de seguridad en `torch.load`:** Actualmente se utiliza con `weights_only=False`, lo que podría permitir cargas inseguras. Recomendado cambiar a `weights_only=True`.

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT.