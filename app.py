import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN IA (CORRECCIÓN DE RUTA 404) ---
try:
    genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
    # Usamos la ruta completa del modelo para forzar la compatibilidad
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de configuración: {e}")

st.set_page_config(page_title="Sanofi Regulatory AI", layout="wide", page_icon="🛡️")

# --- ESTILOS PROFESIONALES ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton>button { 
        width: 100%; 
        border-radius: 20px; 
        background-color: #002D72; 
        color: white; 
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MEMORIA DE SESIÓN ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Conexión actualizada! Ya puedes indexar normativas y solicitar informes."}]
if "memoria_normativa" not in st.session_state:
    st.session_state.memoria_normativa = []

# --- FUNCIONES TÉCNICAS ---
def extraer_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)
    except: return "Error: No se pudo acceder a la URL."

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Carga de Datos")
    fuente = st.radio("Fuente:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
    contenido_nuevo = ""
    if fuente == "Link (URL)":
        u = st.text_input("Pega el enlace:")
        if u: contenido_nuevo = extraer_url(u)
    elif fuente == "Archivo PDF":
        f = st.file_uploader("Sube el PDF:", type="pdf")
        if f:
            reader = PdfReader(f)
            for p in reader.pages: contenido_nuevo += p.extract_text()
    else:
        contenido_nuevo = st.text_area("Pega el texto:")

    if st.button("📥 Indexar a Memoria"):
        if contenido_nuevo and "Error" not in contenido_nuevo:
            st.session_state.memoria_normativa.append(contenido_nuevo)
            st.success(f"Indexado. Fuentes actuales: {len(st.session_state.memoria_normativa)}")

# --- INTERFAZ DE CHAT ---
st.title("🛡️ Monitor de Inteligencia Normativa")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Ej: 'Generar informe de la resolución' o '¿Qué dice sobre diabetes?'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            contexto = "\n---\n".join(st.session_state.memoria_normativa)
            # Instrucción reforzada
            prompt_final = f"""
            Actúa como experto en Market Access de Sanofi.
            CONTEXTO: {contexto[:25000]}
            PREGUNTA: {prompt}
            
            SI EL USUARIO PIDE UN INFORME O ANALIZA NORMAS, RESPONDE ÚNICAMENTE CON UNA TABLA:
            Tipo | Numero | Fecha | Keywords | Resumen | Impacto Sanofi | Impacto Market Access | Fuente
            """
            
            try:
                r = model.generate_content(prompt_final)
                respuesta_texto = r.text
                
                if "|" in respuesta_texto:
                    st.markdown("### Matriz de Impacto:")
                    lineas = [l for l in respuesta_texto.split('\n') if '|' in l]
                    filas = []
                    for l in lineas:
                        partes = [p.strip() for p in l.split("|")]
                        if len(partes) >= 8 and "Tipo" not in partes[0]:
                            filas.append(partes[:8])
                    
                    if filas:
                        df = pd.DataFrame(filas, columns=["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"])
                        st.table(df)
                        csv = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 Descargar para Power BI", csv, "reporte_sanofi.csv", "text/csv")
                else:
                    st.markdown(respuesta_texto)
                
                st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})
            except Exception as e:
                st.error(f"Error de comunicación con la IA: {e}")
