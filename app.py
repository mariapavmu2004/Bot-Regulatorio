import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN E IA ---
genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
model = genai.GenerativeModel('gemini-1.5-flash-latest')

st.set_page_config(page_title="Sanofi Regulatory Chatbot", layout="wide", page_icon="🛡️")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #002D72; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Memoria de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy tu asistente de Inteligencia Normativa. Puedes pegarme links, subir PDFs o simplemente preguntarme por temas ('¿Qué normas hay de enfermedades huérfanas?') o números específicos. Si necesitas el Excel, solo dime 'Dame el informe'."}]
if "contexto_acumulado" not in st.session_state:
    st.session_state.contexto_acumulado = []

# --- FUNCIONES ---
def extraer_de_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e: return f"Error: {str(e)}"

# --- SIDEBAR: CARGA DE DATOS ---
with st.sidebar:
    st.header("⚙️ Centro de Datos")
    fuente = st.radio("Fuente:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
    nuevo_contenido = ""
    if fuente == "Link (URL)":
        url_input = st.text_input("Pega el link aquí:")
        if url_input: nuevo_contenido = extraer_de_url(url_input)
    elif fuente == "Archivo PDF":
        doc = st.file_uploader("Sube el PDF:", type="pdf")
        if doc:
            reader = PdfReader(doc)
            for page in reader.pages: nuevo_contenido += page.extract_text()
    else:
        nuevo_contenido = st.text_area("Pega el texto aquí:")

    if st.button("📥 Indexar a Memoria"):
        if nuevo_contenido and "Error" not in nuevo_contenido:
            st.session_state.contexto_acumulado.append(nuevo_contenido)
            st.success(f"Contenido indexado. Tienes {len(st.session_state.contexto_acumulado)} fuentes en memoria.")

# --- CHATBOT ---
st.title("🛡️ Sanofi Regulatory AI Assistant")

for message in st.session_state.messages:
    with st.chat_message(message["role"]): st.markdown(message["content"])

if prompt := st.chat_input("Escribe lo que necesites (ej. 'Normas de precios', 'Resolución 123', 'Informe')..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando memoria normativa..."):
            # Unimos todo lo que el bot ha leído para que tenga memoria de largo plazo en la sesión
            contexto_total = "\n---\n".join(st.session_state.contexto_acumulado)
            
            instrucciones = f"""
            MEMORIA DISPONIBLE: {contexto_total[:20000]}
            
            PETICIÓN DEL USUARIO: {prompt}
            
            INSTRUCCIONES DE RESPUESTA:
            1. Si el usuario pide un 'Informe', 'Excel', 'Tabla' o analiza una norma específica, responde ÚNICAMENTE con la tabla separada por | :
               Tipo | Numero | Fecha | Keywords | Resumen | Impacto Sanofi | Impacto Market Access | Fuente
            2. Si el usuario pregunta por un tema general (ej. '¿Qué normas hablan de X?'), busca en la memoria y haz un listado breve de lo hallado.
            3. Si pregunta por un número de norma, busca específicamente esa información.
            4. Si la información no está en la memoria, indícalo amablemente.
            """
            
            try:
                response = model.generate_content(instrucciones)
                res_text = response.text
                
                # Lógica para mostrar tabla y botón de descarga automáticamente
                if "|" in res_text:
                    st.markdown("He generado el análisis estructurado:")
                    lineas = [l for l in res_text.split('\n') if '|' in l]
                    # Procesar múltiples filas si la IA detecta varias normas
                    lista_datos = []
                    for fila in lineas:
                        partes = [p.strip() for p in fila.split("|")]
                        if len(partes) >= 8 and partes[0] != "Tipo": # Evitar encabezados repetidos
                            lista_datos.append(partes[:8])
                    
                    if lista_datos:
                        df = pd.DataFrame(lista_datos, columns=["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"])
                        st.table(df)
                        csv = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 Descargar reporte para Power BI", csv, "analisis_sanofi.csv", "text/csv")
                    else:
                        st.markdown(res_text)
                else:
                    st.markdown(res_text)
                
                st.session_state.messages.append({"role": "assistant", "content": res_text})
            except Exception as e:
                st.error(f"Error: {e}")
