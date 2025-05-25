# src/auth/google_auth.py
from flask import Flask, session, redirect, url_for
from flask_session import Session
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv

# ────────────────────────────────────────────────────────────────────────────────
# Cargar variables de entorno desde .env
# ────────────────────────────────────────────────────────────────────────────────
load_dotenv()                     # lee el archivo .env automáticamente

app = Flask(__name__)

# SECRET_KEY para la sesión de Flask
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

oauth = OAuth(app)

app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ────────────────────────────────────────────────────────────────────────────────
# Configuración de Google OAuth usando variables de entorno
# ────────────────────────────────────────────────────────────────────────────────
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    api_base_url="https://www.googleapis.com/oauth2/v1/",
    client_kwargs={"scope": "openid email profile"},
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
)

@app.route('/get_user')
def get_user():
    if 'user' in session:
        return session['user']  # Devuelve la información del usuario
    return {"error": "No autenticado"}  # Devuelve un error si no está autenticado

@app.route('/login')
def login():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    session['user'] = {  # Guarda la información del usuario en la sesión
        'name': user_info['name'],
        'email': user_info['email'],
        'picture': user_info['picture'],
    }
    return "Autenticación exitosa. Puedes cerrar esta pestaña."

@app.route('/logout')
def logout():
    session.pop('user', None)  # Elimina al usuario de la sesión
    return "Cerraste sesión correctamente."
