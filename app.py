import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN IA ---
# Usamos el nombre de modelo estándar para evitar el error 404
try:
    genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error en la configuración inicial: {e}")

st.set_page_config(page_title="Sanofi Regulatory AI", layout="wide", page_icon="🛡️")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #002D72; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Memoria de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! He reiniciado mi conexión. ¿Qué normativa vamos a analizar hoy?"}]
if "memoria_normativa" not in st.session_state:
    st.session_state.memoria_normativa = []

# --- FUNCIONES ---
def extraer_url(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except: return "Error al leer URL"

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Carga de Información")
    fuente = st.radio("Fuente:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
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
            st.success(f"Indexado. Tienes {len(st.session_state.memoria_normativa)} fuentes.")

# --- CHAT ---
st.title("🛡️ Monitor de Inteligencia Normativa")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Escribe tu duda o 'Dame el informe'..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            contexto = "\n---\n".join(st.session_state.memoria_normativa)
            # Prompt optimizado para evitar errores de formato
            prompt_final = f"Contexto: {contexto[:20000]}\n\nPregunta: {prompt}\n\nREGLA: Si el usuario pide un informe o analiza una norma, responde SOLAMENTE con una tabla usando el formato: Tipo | Numero | Fecha | Keywords | Resumen | Impacto Sanofi | Impacto Market Access | Fuente"
            
            try:
                r = model.generate_content(prompt_final)
                t = r.text
                
                if "|" in t:
                    st.markdown("Análisis generado:")
                    lineas = [l for l in t.split('\n') if '|' in l]
                    filas = []
                    for l in lineas:
                        partes = [p.strip() for p in l.split("|")]
                        if len(partes) >= 8 and "Tipo" not in partes[0]:
                            filas.append(partes[:8])
                    
                    if filas:
                        df = pd.DataFrame(filas, columns=["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"])
                        st.table(df)
                        csv = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 Descargar reporte", csv, "analisis.csv", "text/csv")
                else:
                    st.markdown(t)
                
                st.session_state.messages.append({"role": "assistant", "content": t})
            except Exception as e:
                st.error(f"Hubo un problema con la IA: {e}")
