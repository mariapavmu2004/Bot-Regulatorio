import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE SEGURIDAD PARA IA ---
API_KEY = "AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM"
genai.configure(api_key=API_KEY)

# Intentamos cargar el modelo con el nombre más compatible del 2026
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="Sanofi Regulatory AI", layout="wide", page_icon="🛡️")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #002D72; color: white; }
    </style>
    """, unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Conexión forzada exitosa! ¿Qué normativa vamos a procesar hoy?"}]
if "memoria_normativa" not in st.session_state:
    st.session_state.memoria_normativa = []

# --- FUNCIONES ---
def extraer_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        return BeautifulSoup(res.text, 'html.parser').get_text(separator=' ', strip=True)
    except: return "Error al leer URL"

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Carga de Datos")
    fuente = st.radio("Fuente:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
    contenido_nuevo = ""
    if fuente == "Link (URL)":
        u = st.text_input("Pega el link:")
        if u: contenido_nuevo = extraer_url(u)
    elif fuente == "Archivo PDF":
        f = st.file_uploader("Sube PDF:", type="pdf")
        if f:
            reader = PdfReader(f)
            for p in reader.pages: contenido_nuevo += p.extract_text()
    else:
        contenido_nuevo = st.text_area("Pega el texto:")

    if st.button("📥 Indexar a Memoria"):
        if contenido_nuevo and "Error" not in contenido_nuevo:
            st.session_state.memoria_normativa.append(contenido_nuevo)
            st.success("Información indexada.")

# --- CHAT ---
st.title("🛡️ Monitor de Inteligencia Normativa")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Escribe tu consulta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando con la IA..."):
            contexto = "\n---\n".join(st.session_state.memoria_normativa)
            prompt_final = f"CONTEXTO: {contexto[:20000]}\n\nPREGUNTA: {prompt}\n\nSi pides informe, usa formato tabla con |."
            
            try:
                response = model.generate_content(prompt_final)
                res_text = response.text
                
                if "|" in res_text:
                    lineas = [l for l in res_text.split('\n') if '|' in l]
                    filas = [l.split("|") for l in lineas if "Tipo" not in l and len(l.split("|")) >= 5]
                    if filas:
                        df = pd.DataFrame(filas)
                        st.table(df)
                else:
                    st.markdown(res_text)
                
                st.session_state.messages.append({"role": "assistant", "content": res_text})
            except Exception as e:
                st.error(f"Error persistente: {e}. Intenta reiniciar la App desde el panel de Streamlit.")
