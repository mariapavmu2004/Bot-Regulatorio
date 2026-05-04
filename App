import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import io

# CONFIGURACIÓN
genai.configure(api_key="AIzaSyA4Fvxgn4p7LBSAro3p0YNkw18mLiWPg1U")
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Sanofi MA Bot", layout="wide")
st.title("🛡️ Monitor de Inteligencia Normativa")

# CARGA DE DATOS
st.sidebar.header("Entrada de Información")
opcion = st.sidebar.radio("Fuente:", ["Subir PDF Manual", "Pegar Texto de URL"])
texto_para_analizar = ""

if opcion == "Subir PDF Manual":
    archivo = st.sidebar.file_uploader("Sube la normativa (PDF)", type="pdf")
    if archivo:
        pdf = PdfReader(archivo)
        for page in pdf.pages:
            texto_para_analizar += page.extract_text()
else:
    texto_para_analizar = st.sidebar.text_area("Pega aquí el contenido de la web:")

if texto_para_analizar:
    if st.button("Analizar Normativa e Impacto"):
        # Instrucciones específicas para que la IA entienda el contexto de Sanofi y MA
        prompt = f"""
        Eres un experto en Market Access y Asuntos Regulatorios. Analiza el siguiente texto: {texto_para_analizar[:10000]}
        
        Genera una respuesta con estos campos exactamente, separados por el símbolo pipe (|):
        Tipo de Normativa | Numero de Norma | Fecha (DD/MM/AAAA) | Keywords (máximo 4) | Resumen (máximo 6 líneas) | Impacto Sanofi | Impacto Market Access | Fuente
        
        Asegúrate de que el impacto en Market Access sea muy detallado en términos de precio y reembolso.
        """
        response = model.generate_content(prompt)
        
        # Procesar los datos para el Excel
        datos = response.text.split("|")
        columnas = ["Tipo", "Numero", "Fecha", "Keywords", "Resumen", "Impacto Sanofi", "Impacto MA", "Fuente"]
        
        df = pd.DataFrame([datos], columns=columnas)
        st.table(df)
        
        # Botón de descarga
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Excel (.csv) para Power BI", csv, "actualizacion_normativa.csv", "text/csv")
