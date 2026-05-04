import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import io

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Monitor Market Access", layout="wide", page_icon="🛡️")

# --- 2. CONEXIÓN CON IA (CON RESPALDO) ---
API_KEY = "AIzaSyC4HTSZEyi88p98QKo60hlG_ovP2GqtYdM"

@st.cache_resource
def iniciar_modelo():
    try:
        genai.configure(api_key=API_KEY)
        # Intentamos con flash, si el entorno está desactualizado, saltamos a pro
        try:
            return genai.GenerativeModel('gemini-1.5-flash')
        except:
            return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        return None

model = iniciar_modelo()

# --- 3. URLS DE MONITOREO ---
URLS_MONITOREO = [
    "https://www.minsalud.gov.co/Normatividad_Nuevo/Forms/AllItems.aspx",
    "https://www.invima.gov.co/normatividad",
    "https://www.suin-juriscol.gov.co/"
]

# --- 4. FUNCIONES ROBUSTAS DE EXTRACCIÓN ---
def extraer_contenido_web(url):
    """Extrae texto de una URL evitando bloqueos y colapsos."""
    try:
        # Simulamos ser un navegador real para evitar bloqueos del gobierno
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Timeout de 15 segundos para que la app no se quede congelada
        response = requests.get(url, headers=headers, timeout=15)
        
        # Si la página responde con error (ej. 404 o 500 de su lado), lo atrapamos
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Limpiamos código basura
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
            
        texto_limpio = soup.get_text(separator=' ', strip=True)
        return texto_limpio[:12000] # Limitamos caracteres para no saturar la IA
        
    except requests.exceptions.Timeout:
        return "[Error: La página tardó demasiado en responder]"
    except Exception as e:
        return f"[Error al acceder a la fuente: {e}]"

# --- 5. LÓGICA DE INTERFAZ Y SESIÓN ---
if "base_conocimiento" not in st.session_state:
    st.session_state.base_conocimiento = ""
if "df_alertas" not in st.session_state:
    st.session_state.df_alertas = pd.DataFrame()

st.title("🛡️ Monitor Automatizado de Inteligencia Normativa")
st.markdown("Sistema de vigilancia temprana para Market Access.")

# --- SECCIÓN A: PANEL DE CONTROL Y ALERTAS ---
st.subheader("📡 Escaneo de Fuentes Oficiales")

if st.button("🔄 Ejecutar Escaneo Diario y Generar Alertas", type="primary"):
    if model is None:
        st.error("Error crítico: No se pudo conectar con la IA. Revisa la API Key.")
    else:
        with st.spinner("Extrayendo datos de Minsalud, Invima y SUIN..."):
            contenido_acumulado = ""
            for url in URLS_MONITOREO:
                texto_url = extraer_contenido_web(url)
                contenido_acumulado += f"\n--- FUENTE: {url} ---\n{texto_url}\n"
            
            st.session_state.base_conocimiento = contenido_acumulado
            
        with st.spinner("Procesando impacto en enfermedades huérfanas..."):
            prompt_alertas = f"""
            Actúa como experto regulatorio. Analiza el siguiente texto extraído de páginas oficiales.
            Identifica ÚNICAMENTE resoluciones, decretos o circulares que afecten al sector salud, específicamente temas de presupuestos máximos, registros sanitarios o enfermedades huérfanas.
            
            Genera una tabla estricta separada por el símbolo | con estas columnas exactas:
            Tipo|Número|Fecha|Resumen Breve|Nivel de Impacto|Prioridad
            
            Si no hay datos relevantes, responde "No hay actualizaciones relevantes hoy."
            
            TEXTO A ANALIZAR:
            {st.session_state.base_conocimiento[:30000]}
            """
            
            try:
                res = model.generate_content(prompt_alertas)
                texto_respuesta = res.text.strip()
                
                # Procesamos la respuesta para convertirla en DataFrame seguro
                if "|" in texto_respuesta:
                    lineas = [l.strip() for l in texto_respuesta.split('\n') if '|' in l]
                    # Filtramos la fila de encabezados si la IA la genera por defecto
                    datos = [l.split('|') for l in lineas if "Tipo" not in l and "---" not in l]
                    
                    # Validamos que todas las filas tengan 6 columnas para evitar errores de pandas
                    datos_limpios = [fila for fila in datos if len(fila) >= 6]
                    
                    if datos_limpios:
                        # Tomamos solo las primeras 6 columnas en caso de que la IA agregue extras
                        datos_limpios = [fila[:6] for fila in datos_limpios]
                        df = pd.DataFrame(datos_limpios, columns=["Tipo", "Número", "Fecha", "Resumen Breve", "Nivel de Impacto", "Prioridad"])
                        st.session_state.df_alertas = df
                        st.success("✅ Escaneo completado. Alertas generadas.")
                    else:
                        st.warning("Se detectó información, pero no tiene el formato normativo esperado.")
                else:
                    st.info("La IA determinó que no hay actualizaciones relevantes en las fuentes hoy.")
                    
            except Exception as e:
                st.error(f"Error al procesar la información con la IA: {e}")

# --- SECCIÓN B: VISUALIZACIÓN Y DESCARGA ---
if not st.session_state.df_alertas.empty:
    st.markdown("### 📊 Alertas Detectadas")
    st.dataframe(st.session_state.df_alertas, use_container_width=True)
    
    # Botón de descarga en Excel seguro
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        st.session_state.df_alertas.to_excel(writer, index=False, sheet_name='Monitoreo_Diario')
    
    st.download_button(
        label="📥 Descargar Matriz en Excel",
        data=output.getvalue(),
        file_name="matriz_alertas_regulatorias.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- SECCIÓN C: CONSULTORÍA IA ---
st.markdown("---")
st.subheader("💬 Asistente Regulatorio")
pregunta = st.chat_input("Ej: ¿Se menciona algo sobre logística o precios en los enlaces escaneados?")

if pregunta:
    with st.chat_message("user"):
        st.markdown(pregunta)
    
    with st.chat_message("assistant"):
        if not st.session_state.base_conocimiento:
            st.warning("⚠️ Primero debes ejecutar el escaneo (botón de arriba) para que pueda leer las fuentes.")
        else:
            with st.spinner("Analizando la memoria temporal..."):
                prompt_busqueda = f"""
                Basado EXCLUSIVAMENTE en este texto extraído de fuentes oficiales: 
                {st.session_state.base_conocimiento[:30000]}
                
                Responde de forma clara y corporativa a esta consulta: {pregunta}
                Si la respuesta no está en el texto proporcionado, indícalo claramente.
                """
                try:
                    respuesta = model.generate_content(prompt_busqueda)
                    st.markdown(respuesta.text)
                except Exception as e:
                    st.error(f"La IA experimentó un error temporal: {e}")
