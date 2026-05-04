import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN IA ---
genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Sanofi Regulatory AI", layout="wide", page_icon="🛡️")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #002D72; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Memoria de la sesión actual
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy tu asistente de Market Access. Sube los archivos o links de hoy y dime 'Dame el informe' cuando estés lista."}]
if "memoria_normativa" not in st.session_state:
    st.session_state.memoria_normativa = []

# --- FUNCIONES ---
def extraer_url(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        return BeautifulSoup(res.text, 'html.parser').get_text(separator=' ', strip=True)
    except: return "Error al leer URL"

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Carga de Información")
    fuente = st.radio("Tipo de fuente:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
    contenido = ""
    if fuente == "Link (URL)":
        u = st.text_input("Pega el link:")
        if u: contenido = extraer_url(u)
    elif fuente == "Archivo PDF":
        f = st.file_uploader("Sube PDF:", type="pdf")
        if f:
            reader = PdfReader(f)
            for p in reader.pages: contenido += p.extract_text()
    else:
        contenido = st.text_area("Pega el texto:")

    if st.button("📥 Indexar para análisis"):
        if contenido and "Error" not in contenido:
            st.session_state.memoria_normativa.append(contenido)
            st.success(f"Indexado. Tienes {len(st.session_state.memoria_normativa)} fuentes en memoria.")

# --- CHAT ---
st.title("🛡️ Monitor de Inteligencia Normativa")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("¿Qué quieres saber de las normas indexadas?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            contexto = "\n---\n".join(st.session_state.memoria_normativa)
            prompt_final = f"CONTEXTO: {contexto[:20000]}\n\nUSUARIO: {prompt}\n\nREGLA: Si pide informe o analiza normas, usa el formato tabla con |."
            
            try:
                r = model.generate_content(prompt_final)
                t = r.text
                if "|" in t:
                    lineas = [l for l in t.split('\n') if '|' in l]
                    filas = [l.split("|") for l in lineas if "Tipo" not in l and len(l.split("|")) >= 8]
                    if filas:
                        df = pd.DataFrame(filas, columns=["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"])
                        st.table(df)
                        st.download_button("📥 Descargar para Power BI", df.to_csv(index=False).encode('utf-8-sig'), "reporte.csv", "text/csv")
                else: st.markdown(t)
                st.session_state.messages.append({"role": "assistant", "content": t})
            except Exception as e: st.error(f"Error: {e}")
