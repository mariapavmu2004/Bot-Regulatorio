import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup
import os

# --- CONFIGURACIÓN IA ---
# Forzamos el uso de gemini-pro que es el más compatible universalmente
try:
    genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
    # Intentamos con gemini-pro para saltar el error de versión de flash
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"Error de configuración: {e}")

st.set_page_config(page_title="Sanofi Regulatory AI", layout="wide", page_icon="🛡️")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #002D72; color: white; }
    </style>
    """, unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Conexión reestablecida con Gemini Pro! Listo para analizar normativas."}]
if "memoria_normativa" not in st.session_state:
    st.session_state.memoria_normativa = []

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Carga de Datos")
    fuente = st.radio("Fuente:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
    contenido_nuevo = ""
    if fuente == "Link (URL)":
        u = st.text_input("Pega el enlace:")
        if u:
            try:
                res = requests.get(u, timeout=10)
                contenido_nuevo = BeautifulSoup(res.text, 'html.parser').get_text()
            except: st.error("No se pudo leer la URL")
    elif fuente == "Archivo PDF":
        f = st.file_uploader("Sube el PDF:", type="pdf")
        if f:
            reader = PdfReader(f)
            for p in reader.pages: contenido_nuevo += p.extract_text()
    else:
        contenido_nuevo = st.text_area("Pega el texto:")

    if st.button("📥 Indexar a Memoria"):
        if contenido_nuevo:
            st.session_state.memoria_normativa.append(contenido_nuevo)
            st.success(f"Indexado correctamente.")

# --- CHAT ---
st.title("🛡️ Monitor de Inteligencia Normativa")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Escribe tu consulta aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generando respuesta con Gemini Pro..."):
            contexto = "\n---\n".join(st.session_state.memoria_normativa)
            prompt_final = f"Contexto: {contexto[:20000]}\n\nPregunta: {prompt}. Si es un informe, usa tablas."
            
            try:
                # Aquí ocurre la magia
                r = model.generate_content(prompt_final)
                respuesta = r.text
                
                if "|" in respuesta:
                    lineas = [l for l in respuesta.split('\n') if '|' in l]
                    filas = [l.split("|") for l in lineas if "Tipo" not in l and len(l.split("|")) >= 5]
                    if filas:
                        st.table(filas)
                else:
                    st.markdown(respuesta)
                
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
            except Exception as e:
                st.error(f"Error crítico: {e}. Por favor, verifica que la librería google-generativeai esté actualizada en requirements.txt")
