import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader

# Configuración básica
st.set_page_config(page_title="Sanofi Regulatory AI", layout="wide")

# Configurar API
genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")

# Seleccionar modelo (usando el nombre más estándar posible)
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🛡️ Monitor Normativo - Sanofi")

if "memoria" not in st.session_state:
    st.session_state.memoria = ""

# Carga de archivos sencilla para probar
archivo = st.file_uploader("Sube una norma (PDF) para desbloquear la IA", type="pdf")

if archivo:
    reader = PdfReader(archivo)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    st.session_state.memoria = texto
    st.success("Archivo cargado y leído correctamente.")

# Chat
pregunta = st.chat_input("¿Qué quieres saber de la norma?")

if pregunta:
    with st.chat_message("user"):
        st.write(pregunta)
    
    with st.chat_message("assistant"):
        try:
            # Enviamos el contenido junto a la pregunta
            prompt = f"Basado en este texto: {st.session_state.memoria[:15000]}\n\nPregunta: {pregunta}"
            response = model.generate_content(prompt)
            st.write(response.text)
        except Exception as e:
            st.error(f"Error técnico: {e}")
            st.info("Si el error es 404, por favor haz clic en 'Manage App' -> 'Reboot App' en el panel de Streamlit.")
