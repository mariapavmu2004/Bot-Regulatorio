import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN E IA ---
# Se ha actualizado con la llave proporcionada
genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
model = genai.GenerativeModel('gemini-1.5-flash')

# Configuración de página con estética profesional para Sanofi
st.set_page_config(page_title="Sanofi Regulatory Chatbot", layout="wide", page_icon="🛡️")

# Estilos personalizados para la interfaz de chat y botones
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
    .stSidebar { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA DEL CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy tu asistente de Market Access. Estoy listo para procesar normativas. ¿Deseas analizar un link, un PDF o pegarme el texto directamente?"}
    ]
if "contexto_normativo" not in st.session_state:
    st.session_state.contexto_normativo = ""

# --- FUNCIONES DE EXTRACCIÓN ---
def extraer_de_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        for script_or_style in soup(["script", "style"]):
            script_or_style.extract()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Error al leer la URL: {str(e)}"

# --- BARRA LATERAL (CENTRO DE CARGA) ---
with st.sidebar:
    st.header("⚙️ Entrada de Información")
    fuente = st.radio("Selecciona la fuente de la norma:", ["Link (URL)", "Archivo PDF", "Texto Manual"])
    
    nuevo_contenido = ""
    if fuente == "Link (URL)":
        url_input = st.text_input("Pega el enlace oficial aquí:")
        if url_input:
            with st.spinner("Accediendo a la web..."):
                nuevo_contenido = extraer_de_url(url_input)
    
    elif fuente == "Archivo PDF":
        doc = st.file_uploader("Sube el PDF de la normativa:", type="pdf")
        if doc:
            with st.spinner("Procesando documento..."):
                reader = PdfReader(doc)
                for page in reader.pages:
                    nuevo_contenido += page.extract_text()
    
    else:
        nuevo_contenido = st.text_area("Pega el contenido legal aquí:")

    if st.button("📥 Sincronizar con el Chatbot"):
        if nuevo_contenido and "Error" not in nuevo_contenido:
            st.session_state.contexto_normativo = nuevo_contenido
            st.success("¡Información cargada con éxito!")
        elif "Error" in nuevo_contenido:
            st.error(nuevo_contenido)

# --- PANEL PRINCIPAL (INTERFAZ DE CHATBOT) ---
st.title("🛡️ Sanofi Regulatory AI Assistant")
st.caption("Análisis estratégico de normativas para Market Access y cumplimiento institucional.")

# Mostrar historial de la conversación
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del Chat
if prompt := st.chat_input("Escribe tu duda o solicita el 'Generar Informe'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta generada por la IA
    with st.chat_message("assistant"):
        with st.spinner("Analizando impacto regulatorio..."):
            instrucciones_ia = f"""
            Contexto de la Normativa: {st.session_state.contexto_normativo[:15000]}
            
            Acción solicitada: {prompt}
            
            INSTRUCCIONES CLAVE:
            - Si el usuario pide un 'Análisis', 'Informe' o 'Resumen', genera una tabla separada por el símbolo | con estas columnas:
              Tipo | Numero | Fecha (DD/MM/AAAA) | Keywords (Max 4) | Resumen (Max 6 líneas) | Impacto Sanofi | Impacto Market Access | Fuente
            
            - Impacto Sanofi: Evalúa relevancia institucional y portafolio.
            - Impacto Market Access: Evalúa barreras de entrada, precios, reembolsos y acceso.
            """
            
            try:
                response = model.generate_content(instrucciones_ia)
                texto_respuesta = response.text
                
                # Detectar si la respuesta contiene la estructura de la tabla
                if "|" in texto_respuesta and "Tipo" in texto_respuesta:
                    st.markdown("He procesado la normativa. Aquí tienes la matriz de impacto:")
                    
                    # Extracción de la fila de datos
                    lineas = [l for l in texto_respuesta.split('\n') if '|' in l]
                    datos_fila = [d.strip() for d in lineas[-1].split("|")]
                    
                    if len(datos_fila) >= 8:
                        columnas = ["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"]
                        df_reporte = pd.DataFrame([datos_fila[:8]], columns=columnas)
                        st.table(df_reporte)
                        
                        # Preparación para descarga (Power BI)
                        csv_data = df_reporte.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Descargar Reporte para Power BI",
                            data=csv_data,
                            file_name="matriz_regulatoria_sanofi.csv",
                            mime="text/csv"
                        )
                    else:
                        st.markdown(texto_respuesta)
                else:
                    st.markdown(texto_respuesta)
                
                st.session_state.messages.append({"role": "assistant", "content": texto_respuesta})
                
            except Exception as e:
                st.error(f"Error de conexión con Gemini: {str(e)}")
