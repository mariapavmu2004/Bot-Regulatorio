import streamlit as st
import pandas as pd
import google.generativeai as genai
from PyPDF2 import PdfReader
import io

# --- CONFIGURACIÓN DE IDENTIDAD Y SEGURIDAD ---
st.set_page_config(page_title="Sanofi Market Access Bot", layout="wide", page_icon="🛡️")

# Configuración del modelo con la ruta corregida para evitar el 404
try:
    genai.configure(api_key="AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM")
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- GESTIÓN DE MEMORIA (ALERTAS) ---
if "alertas_registradas" not in st.session_state:
    st.session_state.alertas_registradas = []

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ Sistema de Alertas Regulatorias - Market Access")
st.markdown("---")

# Columna izquierda: Carga y Generación | Columna derecha: Visualización de Alertas
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 Cargar Nueva Normativa")
    archivo = st.file_uploader("Sube el PDF de la resolución o decreto:", type="pdf")
    
    if archivo:
        reader = PdfReader(archivo)
        texto_norma = "".join([page.extract_text() for page in reader.pages])
        
        if st.button("🚀 Generar Alerta y Analizar Impacto"):
            with st.spinner("IA analizando impacto en patologías huérfanas..."):
                # Prompt estructurado para forzar el formato de datos
                prompt = f"""
                Analiza esta norma para el área de Market Access en Sanofi. 
                Extrae la información y responde ÚNICAMENTE en este formato separado por punto y coma (;):
                Tipo de Norma;Número;Fecha;Resumen;Impacto Sanofi;Prioridad (Alta/Media/Baja)

                TEXTO: {texto_norma[:10000]}
                """
                
                try:
                    response = model.generate_content(prompt)
                    datos = response.text.strip().split(";")
                    
                    if len(datos) >= 6:
                        nueva_alerta = {
                            "Tipo": datos[0],
                            "Número": datos[1],
                            "Fecha": datos[2],
                            "Resumen": datos[3],
                            "Impacto": datos[4],
                            "Prioridad": datos[5]
                        }
                        st.session_state.alertas_registradas.append(nueva_alerta)
                        st.success("✅ Alerta generada y guardada en el sistema.")
                    else:
                        st.error("La IA no pudo estructurar los datos. Intenta con otro archivo.")
                except Exception as e:
                    st.error(f"Error técnico: {e}")

with col2:
    st.subheader("🔔 Panel de Alertas Recientes")
    if st.session_state.alertas_registradas:
        df = pd.DataFrame(st.session_state.alertas_registradas)
        st.dataframe(df, use_container_width=True)
        
        # --- GENERACIÓN DE EXCEL ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Alertas_Regulatorias')
        
        st.download_button(
            label="📊 Descargar Reporte en Excel",
            data=output.getvalue(),
            file_name="reporte_regulatorio_sanofi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay alertas registradas todavía.")

# --- SECCIÓN DE CONSULTA LIBRE ---
st.markdown("---")
st.subheader("💬 Consultoría IA sobre Normativa Indexada")
pregunta = st.chat_input("¿Cómo afecta esta norma al acceso de medicamentos para enfermedades huérfanas?")

if pregunta and st.session_state.alertas_registradas:
    contexto = str(st.session_state.alertas_registradas)
    r = model.generate_content(f"Contexto de alertas: {contexto}\nPregunta: {pregunta}")
    with st.chat_message("assistant"):
        st.markdown(r.text)
