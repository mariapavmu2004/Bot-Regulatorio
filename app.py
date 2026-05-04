import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup

# CONFIGURACIÓN - Reemplaza con tu API Key nueva
genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Sanofi MA Bot", layout="wide")
st.title("🛡️ Monitor de Inteligencia Normativa")

# --- FUNCIONES DE EXTRACCIÓN ---
def extraer_de_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Eliminamos scripts y estilos para limpiar el texto
        for script in soup(["script", "style"]):
            script.extract()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        return f"Error al leer la URL: {e}"

# --- INTERFAZ ---
st.sidebar.header("Entrada de Información")
opcion = st.sidebar.radio("Fuente:", ["Pegar Link (URL)", "Subir PDF Manual", "Pegar Texto directamente"])

texto_para_analizar = ""

if opcion == "Pegar Link (URL)":
    url_input = st.sidebar.text_input("Pega el link de la normativa:")
    if url_input:
        with st.spinner("Leyendo contenido de la web..."):
            texto_para_analizar = extraer_de_url(url_input)

elif opcion == "Subir PDF Manual":
    archivo = st.sidebar.file_uploader("Sube la normativa (PDF)", type="pdf")
    if archivo:
        pdf = PdfReader(archivo)
        for page in pdf.pages:
            texto_para_analizar += page.extract_text()

else:
    texto_para_analizar = st.sidebar.text_area("Pega aquí el contenido de la web o el resumen:")

# --- PROCESAMIENTO ---
if texto_para_analizar:
    if "Error al leer" in texto_para_analizar:
        st.error(texto_para_analizar)
    else:
        if st.button("🚀 Analizar Normativa e Impacto"):
            with st.spinner("La IA está analizando la información..."):
                prompt = f"""
                Analiza el siguiente contenido legal: {texto_para_analizar[:10000]}
                
                Genera una tabla con estos campos EXACTOS, separados por el símbolo pipe (|):
                Tipo de Normativa | Numero de Norma | Fecha (DD/MM/AAAA) | Keywords (máximo 4) | Resumen (máximo 6 líneas) | Impacto Sanofi | Impacto Market Access | Fuente
                
                Instrucciones de impacto:
                - Sanofi: Relevancia para el portafolio y cumplimiento.
                - Market Access: Barreras de entrada, precios y reembolso.
                """
                
                try:
                    response = model.generate_content(prompt)
                    # Limpiamos posibles espacios en blanco extras
                    datos = [d.strip() for d in response.text.split("|")]
                    
                    columnas = ["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"]
                    
                    if len(datos) >= 8:
                        df = pd.DataFrame([datos[:8]], columns=columnas)
                        st.success("¡Análisis completado!")
                        st.table(df)
                        
                        csv = df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 Descargar para Power BI", csv, "actualizacion.csv", "text/csv")
                    else:
                        st.warning("La IA no pudo formatear la tabla correctamente. Intenta de nuevo.")
                        st.write(response.text)
                except Exception as e:
                    st.error(f"Hubo un problema con la IA: {e}")
                    # Lista de URLs maestras que el área siempre debe monitorear
URLS_MONITOREO = [
    "https://www.minsalud.gov.co/Normatividad_Nuevo/Forms/AllItems.aspx",
    "https://www.invima.gov.co/procesos-normativos"
]

def monitoreo_automatico():
    st.subheader("🕵️ Estado de Monitoreo Constante")
    for url in URLS_MONITOREO:
        # El bot intenta leer estas URLs automáticamente cada vez que se abre
        contenido = extraer_de_url(url)
        if contenido:
            st.write(f"✅ Conexión activa con: {url}")
        else:
            st.write(f"⚠️ Alerta: No se pudo acceder a {url}")
