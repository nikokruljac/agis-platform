# =====================================================================
# PLATAFORMA INTEGRADA AGIS v5.4.1 - CÓDIGO COMPLETO Y CORREGIDO
# =====================================================================

import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
import json
import pandas as pd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from PIL import Image
import os  # <--- IMPORTANTE: 'os' se importa aquí arriba
from io import BytesIO
import sqlite3 # <--- IMPORTANTE: 'sqlite3' se importa aquí arriba
import glob
import hashlib

def obtener_ruta_logo():
    # Buscamos 'logo_agis.png' en la carpeta raíz
    if os.path.exists("logo_agis.png"):
        return "logo_agis.png"
    return None

# --- CONFIGURACIÓN DE BASE DE DATOS ---
if not os.path.exists("database"):
    os.makedirs("database")

def inicializar_db():
    # Usamos la ruta absoluta para que siempre encuentre la carpeta database
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "database", "agis_database.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            telefono TEXT,
            perfil TEXT,
            chacras TEXT
        )
    ''')
    
    # Crear administrador por defecto si no existe
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        hash_admin = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO usuarios (nombre, username, password, perfil) 
            VALUES (?, ?, ?, ?)
        ''', ("Administrador", "admin", hash_admin, "Administrador"))
    
    conn.commit()
    conn.close()

inicializar_db()

# Importaciones del motor de maquetación PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import streamlit_authenticator as stauth

# --- LÓGICA DE LOGIN ---
# Esta función busca en tu base de datos si el usuario existe
def verificar_login(username, password):
    conn = sqlite3.connect("database/agis_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM usuarios WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        # Comparamos el hash del input con el hash guardado en DB
        hash_input = hashlib.sha256(password.encode()).hexdigest()
        return result[0] == hash_input 
    return False

# Inicializar el estado de sesión si no existe
if 'logueado' not in st.session_state:
    st.session_state['logueado'] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state['logueado']:
    st.title("🔐 Acceso a Plataforma AGIS")
    user_input = st.text_input("Usuario")
    pass_input = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        if verificar_login(user_input, pass_input):
            st.session_state['logueado'] = True
            st.session_state['usuario'] = user_input
            st.rerun() # Recarga la app para mostrar el contenido
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop() # Detiene la ejecución aquí si no está logueado

# 1. CONFIGURACIÓN DE INTERFAZ Y ESTILOS
st.set_page_config(layout="wide", page_title="Plataforma AGIS", page_icon="🌱", initial_sidebar_state="collapsed")

if "lote_seleccionado" not in st.session_state:
    st.session_state["lote_seleccionado"] = "01"

st.markdown(
    """
    <style>
        [data-testid="stSidebarCollapse"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        div.stButton > button {
            background-color: #28a745 !important; color: white !important;
            font-size: 16px !important; font-weight: bold !important; border-radius: 6px !important;
        }
        .metric-card {
            background-color: #f8f9fa; padding: 15px; border-radius: 8px;
            border-left: 5px solid #28a745; margin-bottom: 10px;
        }
        .status-box {
            padding: 18px; border-radius: 8px; margin-bottom: 12px; color: #ffffff; font-weight: 500;
        }
        .status-success { background-color: #2e7d32; border-left: 6px solid #1b5e20; }
        .status-warning { background-color: #ef6c00; border-left: 6px solid #e65100; }
        .status-error { background-color: #c62828; border-left: 6px solid #b71c1c; }
        
        .report-card {
            background-color: #ffffff; padding: 20px; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eef2f3; margin-bottom: 15px;
        }
        
        .kpi-box {
            padding: 15px; border-radius: 8px; text-align: center; color: white; font-weight: bold;
        }
    </style>
    """,
    unsafe_allow_html=True
)
# 2. MOTOR DE CARGA DINÁMICA (Lee lo que subes desde AGIS Studio)
def obtener_datos_usuario(username):
    ruta_usuario = os.path.join("uploads", username)
    csv_files = glob.glob(os.path.join(ruta_usuario, "**/*.csv"), recursive=True)
    if csv_files:
        df = pd.read_csv(csv_files[0])
        df.columns = df.columns.str.strip()
        # Relleno de seguridad
        df = df.fillna({'porcentaje_alerta': 0.0, 'ndre_actual': 0.0, 'ndmi_actual': 0.0, 'alerta_radar': 'ESTABLE', 'cultivo': 'N/A'})
        df['id_lote_str'] = df['id_lote'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(2) if 'id_lote' in df.columns else "01"
        df['id_chacra'] = df['id_chacra'].astype(str).str.strip() if 'id_chacra' in df.columns else "Chacra"
        return df
    return pd.DataFrame()

# Cargamos el DF del usuario logueado
if st.session_state.get('logueado'):
    df_metricas = obtener_datos_usuario(st.session_state['usuario'])
else:
    df_metricas = pd.DataFrame()
def obtener_ruta_logo():
    return "logo.png" if os.path.exists("logo.png") else ( "logo_agis.png" if os.path.exists("logo_agis.png") else None )

# FUNCIÓN AUXILIAR: CALCULAR TENDENCIAS CON FLECHAS
def calcular_flecha_tendencia(actual, historico, umbral=0.02):
    diff = actual - historico
    if diff > umbral:
        return "▲ Subiendo"
    elif diff < -umbral:
        return "▼ Bajando"
    else:
        return "● Estable"

# 3. MOTOR DE GENERACIÓN PDF (REPORTE EJECUTIVO COMERCIAL)
def exportar_pdf_comercial(df_chacra, nombre_chacra):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#2e7d32'), spaceAfter=3)
    subtitle_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#555555'), spaceAfter=15)
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#1b5e20'), spaceBefore=12, spaceAfter=8)
    body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=6)
    table_text_style = ParagraphStyle('TableText', parent=styles['Normal'], fontSize=8.5, leading=11, alignment=1)
    table_header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.whitesmoke, alignment=1)
    
    ruta_logo = obtener_ruta_logo()
    if ruta_logo:
        try:
            logo_img = RLImage(ruta_logo, width=90, height=45)
            logo_img.hAlign = 'RIGHT'
            t_header = Table([[Paragraph("AGIS — Reporte de Monitoreo Inteligente", title_style), logo_img]], colWidths=[400, 150])
            t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(t_header)
        except:
            story.append(Paragraph("AGIS — Reporte de Monitoreo Inteligente", title_style))
    else:
        story.append(Paragraph("AGIS — Reporte de Monitoreo Inteligente", title_style))
        
    story.append(Paragraph(f"Establecimiento Mapeado: {nombre_chacra} | Capas de Análisis GEE & SAR Core", subtitle_style))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph("1. Diagnóstico de Criticidad y Prioridades", h2_style))
    
    if not df_chacra.empty:
        df_sorted = df_chacra.sort_values(by='porcentaje_alerta', ascending=False)
        tabla_datos = [[
            Paragraph("<b>ID Lote</b>", table_header_style), 
            Paragraph("<b>Cultivo</b>", table_header_style), 
            Paragraph("<b>% Área Afectada</b>", table_header_style), 
            Paragraph("<b>Sanitario (NDRE)</b>", table_header_style), 
            Paragraph("<b>Hídrico (NDMI)</b>", table_header_style)
        ]]
        
        for _, fila in df_sorted.iterrows():
            ndre_val = float(fila.get('ndre_actual', 0.0))
            ndmi_val = float(fila.get('ndmi_actual', 0.0))
            status_ndre = "Óptimo" if ndre_val >= 0.50 else ("Transición" if ndre_val >= 0.25 else "Crítico")
            status_ndmi = "Óptimo" if ndmi_val >= 0.30 else ("Moderado" if ndmi_val >= 0.10 else "Déficit")
            
            tendencia_n = calcular_flecha_tendencia(ndre_val, float(fila.get('ndre_historico', 0.0)))
            
            tabla_datos.append([
                Paragraph(f"Lote {fila['id_lote_str']}", table_text_style),
                Paragraph(str(fila.get('cultivo', 'N/A')).upper(), table_text_style),
                Paragraph(f"{float(fila.get('porcentaje_alerta', 0.0)):.1f} %", table_text_style),
                Paragraph(f"{status_ndre} ({tendencia_n.split()[0]})", table_text_style),
                Paragraph(status_ndmi, table_text_style)
            ])
        
        t = Table(tabla_datos, colWidths=[70, 100, 100, 140, 140])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2e7d32')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eef2f3')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("2. Hojas de Ruta y Órdenes de Recorrido Georreferenciadas", h2_style))
        story.append(Spacer(1, 5))
        
        for _, fila in df_sorted.iterrows():
            p_txt = f"<b>• LOTE {fila['id_lote_str']} ({str(fila.get('cultivo', 'N/A')).upper()}):</b> Superficie Comprometida: {float(fila.get('porcentaje_alerta', 0.0)):.1f}%. Estado Radar: {str(fila.get('alerta_radar', 'ESTABLE')).upper()}."
            story.append(Paragraph(p_txt, body_style))
            story.append(Paragraph("<font color='#888888'><i>Observaciones de campo: __________________________________________________________________________</i></font>", body_style))
            story.append(Spacer(1, 5))
            
    doc.build(story)
    buffer.seek(0)
    return buffer

# GENERADOR DE REPORTE DE DATOS TÉCNICOS EN PDF (CON DECIMALES)
def exportar_pdf_datos_tecnicos(df_chacra, nombre_chacra):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitleData', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1b5e20'), spaceAfter=2)
    subtitle_style = ParagraphStyle('DocSubData', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#666666'), spaceAfter=20)
    table_text_style = ParagraphStyle('TableTextD', parent=styles['Normal'], fontSize=9, leading=12, alignment=1)
    table_header_style = ParagraphStyle('TableHeaderD', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.whitesmoke, alignment=1)
    
    ruta_logo = obtener_ruta_logo()
    if ruta_logo:
        try:
            logo_img = RLImage(ruta_logo, width=80, height=40)
            logo_img.hAlign = 'RIGHT'
            t_header = Table([[Paragraph("AGIS — Anexo de Mediciones Técnicas", title_style), logo_img]], colWidths=[380, 150])
            t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(t_header)
        except:
            story.append(Paragraph("AGIS — Anexo de Mediciones Técnicas", title_style))
    else:
        story.append(Paragraph("AGIS — Anexo de Mediciones Técnicas", title_style))
        
    story.append(Paragraph(f"Establecimiento: {nombre_chacra} | Valores Numéricos Absolutos de Índices", subtitle_style))
    
    tabla_datos = [[
        Paragraph("<b>Lote</b>", table_header_style), 
        Paragraph("<b>Cultivo</b>", table_header_style), 
        Paragraph("<b>% Alerta</b>", table_header_style), 
        Paragraph("<b>Índice NDRE</b>", table_header_style), 
        Paragraph("<b>Índice NDMI</b>", table_header_style)
    ]]
    
    df_sorted = df_chacra.sort_values(by='id_lote_str')
    for _, fila in df_sorted.iterrows():
        tabla_datos.append([
            Paragraph(f"Lote {fila['id_lote_str']}", table_text_style),
            Paragraph(str(fila.get('cultivo', 'N/A')).upper(), table_text_style),
            Paragraph(f"{float(fila.get('porcentaje_alerta', 0.0)):.1f}%", table_text_style),
            Paragraph(f"{float(fila.get('ndre_actual', 0.0)):.2f}", table_text_style),
            Paragraph(f"{float(fila.get('ndmi_actual', 0.0)):.2f}", table_text_style)
        ])
        
    t = Table(tabla_datos, colWidths=[80, 110, 100, 120, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1b5e20')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# 4. PROCESAMIENTO RÁSTER GEORREFERENCIADO (DINÁMICO)
def generar_overlay_con_contraste(nombre_tif, tipo_capa, ruta_carpeta):
    ruta_completa_tif = os.path.join(ruta_carpeta, nombre_tif)
    
    if not os.path.exists(ruta_completa_tif): return None, None
    try:
        dst_crs = 'EPSG:4326'
        with rasterio.open(ruta_completa_tif) as src:
            transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
            nodata_val = src.nodata if src.nodata is not None else -9999
            bandas = []
            for b in range(1, src.count + 1):
                destino = np.zeros((height, width), dtype=np.float32)
                reproject(
                    source=rasterio.band(src, b), destination=destino,
                    src_transform=src.transform, src_crs=src.crs,
                    dst_transform=transform, dst_crs=dst_crs,
                    resampling=Resampling.nearest, init_value=nodata_val
                )
                bandas.append(destino)
            
            left, bottom, right, top = transform * (0, height), transform * (width, height), transform * (width, 0), transform * (0, 0)
            bordes = [[bottom[1], left[0]], [top[1], right[0]]]

            b1 = bandas[0]
            # Búsqueda dinámica de referencia en la carpeta del usuario
            tifs_disponibles = glob.glob(os.path.join(ruta_carpeta, "*.tif"))
            archivo_ref = tifs_disponibles[0] if tifs_disponibles else ruta_completa_tif
            
            with rasterio.open(archivo_ref) as ref_src:
                ref_dest = np.zeros((height, width), dtype=np.float32)
                reproject(
                    source=rasterio.band(ref_src, 1), destination=ref_dest,
                    src_transform=ref_src.transform, src_crs=ref_src.crs,
                    dst_transform=transform, dst_crs=dst_crs,
                    resampling=Resampling.nearest, init_value=-9999
                )
                chacra_mask = (~np.isnan(ref_dest)) & (ref_dest != ref_src.nodata) & (ref_dest != 0.0) & (ref_dest > -900)

            if tipo_capa == "Color Real (RGB)" and src.count >= 3:
                r, g, b = bandas[0], bandas[1], bandas[2]
                mascara_alfa = np.where(chacra_mask, 240, 0).astype(np.uint8)
                
                def estirar_banda(banda, mask):
                    if not mask.any(): return np.zeros_like(banda, dtype=np.uint8)
                    p2, p98 = np.percentile(banda[mask], 2), np.percentile(banda[mask], 98)
                    if p98 == p2: p98 += 1e-5
                    return np.clip((banda - p2) / (p98 - p2) * 255, 0, 255).astype(np.uint8)
                
                img_rgba = np.dstack((estirar_banda(r, chacra_mask), estirar_banda(g, chacra_mask), estirar_banda(b, chacra_mask), mascara_alfa))
                Image.fromarray(img_rgba, 'RGBA').save("temp_view.png")
                return "temp_view.png", bordes
            else:
                matriz_rgba = np.zeros((height, width, 4), dtype=np.uint8)
                if chacra_mask.any():
                    if tipo_capa == "Alertas":
                        matriz_rgba[chacra_mask & (b1 > 0.6)] = [230, 57, 70, 240]
                        matriz_rgba[chacra_mask & (b1 > 0.1) & (b1 <= 0.6)] = [255, 193, 7, 240]
                        matriz_rgba[chacra_mask & (b1 <= 0.1)] = [40, 167, 69, 220]
                    elif tipo_capa == "NDRE":
                        matriz_rgba[(b1 < 0.25) & chacra_mask] = [220, 53, 69, 240]
                        matriz_rgba[(b1 >= 0.25) & (b1 < 0.50) & chacra_mask] = [255, 193, 7, 240]
                        matriz_rgba[(b1 >= 0.50) & chacra_mask] = [40, 167, 69, 240]
                    elif tipo_capa == "NDMI":
                        matriz_rgba[(b1 < 0.10) & chacra_mask] = [240, 128, 128, 230]
                        matriz_rgba[(b1 >= 0.10) & (b1 < 0.30) & chacra_mask] = [255, 239, 184, 230]
                        matriz_rgba[(b1 >= 0.30) & chacra_mask] = [58, 134, 255, 230]
                    else:
                        v_min, v_max = np.percentile(b1[chacra_mask], 2), np.percentile(b1[chacra_mask], 98)
                        if v_max == v_min: v_max += 1e-5
                        val_norm = np.clip((b1 - v_min) / (v_max - v_min), 0.0, 1.0)
                        gris = (val_norm * 255).astype(np.uint8)
                        matriz_rgba[chacra_mask, 0] = gris[chacra_mask]
                        matriz_rgba[chacra_mask, 1] = gris[chacra_mask]
                        matriz_rgba[chacra_mask, 2] = gris[chacra_mask]
                        matriz_rgba[chacra_mask, 3] = 200

                Image.fromarray(matriz_rgba, 'RGBA').save("temp_view.png")
                return "temp_view.png", bordes
    except Exception as e:
        return None, None
# 5. RENDERIZADO DEL ENCABEZADO
col_title, col_brand = st.columns([4.2, 0.8])
with col_title:
    st.title("Plataforma de Monitoreo Inteligente")
    st.caption("Intelligence and Analytics for Precision Agriculture | Powered by GEE & SAR Core")
with col_brand:
    archivo_logo = obtener_ruta_logo()
    if archivo_logo:
        st.image(archivo_logo, width=130)
    else:
        st.markdown("<div style='text-align:right; font-weight:bold; color:#2e7d32; font-size:20px; padding-top:15px;'>AGIS</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Módulo 1: Vista General", 
    "🗺️ Módulo 2: Diagnóstico", 
    "📋 Módulo 3: Reportes",
    "👤 Módulo 4: Mi Perfil",
    "💻 Módulo 5: AGIS Studio"
])
# =====================================================================
# MÓDULO 1: VISTA GENERAL DE CHACRA (ADMIN-SAFE)
# =====================================================================
with tab1:
    st.header("Plan de Recorrido Diario Basado en Riesgo")
    
    # 1. Recuperar datos del usuario y definir alcance
    conn = sqlite3.connect("database/agis_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chacras, perfil FROM usuarios WHERE username = ?", (st.session_state['usuario'],))
    user_data = cursor.fetchone()
    conn.close()
    
    # 2. Lógica de Filtrado Inteligente
    user_perfil = user_data[1] if user_data else "Productor"
    user_chacras = [c.strip() for c in user_data[0].split(',')] if user_data and user_data[0] else []
    
    if user_perfil == 'Administrador':
        df_metricas_usr = df_metricas.copy()
    else:
        df_metricas_usr = df_metricas[df_metricas['id_chacra'].isin(user_chacras)].copy()
    
    # 3. Renderizado del Módulo
    if not df_metricas_usr.empty:
        valor_calidad = df_metricas_usr['calidad_optica'].iloc[0] if 'calidad_optica' in df_metricas_usr.columns else "EXCELENTE"
        
        if "EXCELENTE" in str(valor_calidad).upper():
            icono, estado, color = "☀️", "Condición Óptica: Despejada", "#2e7d32"
        elif "PARCIAL" in str(valor_calidad).upper():
            icono, estado, color = "⛅", "Condición Óptica: Parcial", "#ef6c00"
        else:
            icono, estado, color = "☁️", "Condición Óptica: Nublado", "#c62828"
            
        st.markdown(f"<div style='background-color:{color}; padding:15px; border-radius:8px; color:white; text-align:center; font-weight:bold; font-size:18px; margin-bottom:20px;'>{icono} {estado}</div>", unsafe_allow_html=True)

        df_priorizado = df_metricas_usr.sort_values(by='porcentaje_alerta', ascending=False).copy()
        lotes_criticos = df_priorizado[df_priorizado['porcentaje_alerta'] > 15.0]
        lotes_revision = df_priorizado[(df_priorizado['porcentaje_alerta'] <= 15.0) & (df_priorizado['porcentaje_alerta'] > 2.0)]
        lotes_sanos = df_priorizado[df_priorizado['porcentaje_alerta'] <= 2.0]

        col_k1, col_k2, col_k3 = st.columns(3)
        with col_k1: st.markdown(f"<div class='kpi-box' style='background-color:#c62828;'>🚨 Alerta Máxima: {len(lotes_criticos)} Lotes</div>", unsafe_allow_html=True)
        with col_k2: st.markdown(f"<div class='kpi-box' style='background-color:#ef6c00;'>⚠️ En Revisión: {len(lotes_revision)} Lotes</div>", unsafe_allow_html=True)
        with col_k3: st.markdown(f"<div class='kpi-box' style='background-color:#2e7d32;'>🟢 Lotes Estables: {len(lotes_sanos)} Lotes</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Matriz de Diagnóstico y Priorización de Recorrido")
        st.dataframe(df_priorizado[['id_lote_str', 'cultivo', 'porcentaje_alerta', 'alerta_ndre', 'alerta_ndmi', 'alerta_radar']], use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos disponibles para mostrar.")
# =====================================================================
# MÓDULO 2: DIAGNÓSTICO GEOGRÁFICO (INTEGRACIÓN DINÁMICA)
# =====================================================================

# 1. Definir la función FUERA del flujo de ejecución, idealmente arriba
def obtener_diagnostico_y_recomendacion(lote_row):
    cambio_ndre = float(lote_row.get('cambio_ndre', 0))
    cambio_ndmi = float(lote_row.get('cambio_ndmi', 0))
    desvio_sar = float(lote_row.get('desvio_sar', 0))
    
    if cambio_ndre < -5 and cambio_ndmi < -5 and abs(desvio_sar) > 2:
        return "Estrés severo con impacto estructural", "Priorizar inspección en campo"
    elif cambio_ndre < -5 and cambio_ndmi < -5:
        return "Posible estrés hídrico", "Revisar disponibilidad hídrica y condiciones del suelo"
    elif cambio_ndre < -5 and -5 <= cambio_ndmi <= 5:
        return "Posible limitante nutricional o daño localizado", "Evaluar nutrición y uniformidad del cultivo"
    elif abs(desvio_sar) > 2:
        return "Cambio estructural", "Revisar daños físicos, pisoteo o variabilidad del lote"
    else:
        return "Cultivo estable", "Continuar monitoreo normal"

with tab2:
    st.header("Inspección de Índices y Evidencias")
    
    if 'df_metricas_usr' in locals() and not df_metricas_usr.empty:
        # ... (código de selección de chacra igual)
        chacra_sel = st.selectbox("🏢 Seleccionar Establecimiento / Chacra:", sorted(list(set(df_metricas_usr['id_chacra'].tolist()))), key="sel_chacra_m2_final")
        df_chacra_activa = df_metricas_usr[df_metricas_usr['id_chacra'] == chacra_sel]
        
        if not df_chacra_activa.empty:
            # ... (código de gráficos igual)
            
            st.markdown("---")
            lote_sel = st.selectbox("🎯 Bajar a Detalle Quirúrgico de Lote:", sorted(list(set(df_chacra_activa['id_lote_str'].tolist()))), key="sel_lote_m2_final")
            lote_row = df_chacra_activa[df_chacra_activa['id_lote_str'] == str(lote_sel)].iloc[0]
            
            # (Metricas arriba igual)
            
            # --- AQUÍ EMPIEZA LA CORRECCIÓN DEL LAYOUT ---
            col_izq, col_der = st.columns([1, 1.2])

            with col_izq:
                
    st.markdown(f"### 📋 Diagnóstico Lote {lote_sel}")
    # 1. Definir funciones de estado para los semáforos individuales
    # (Usamos las reglas de cambio que definiste: < -5, -5 a 5, > 5)
    def color_semaforo(valor):
        if valor < -5: return "#c62828"  # Rojo (Caída)
        elif -5 <= valor <= 5: return "#2e7d32" # Verde (Estable)
        else: return "#f39c12" # Amarillo (Posible mejora/cambio)

    # 2. Renderizar los semáforos individuales
    # Extracción de valores
    c_ndre = float(lote_row.get('cambio_ndre', 0))
    c_ndmi = float(lote_row.get('cambio_ndmi', 0))
    d_sar = float(lote_row.get('desvio_sar', 0))

    # Columnas internas para los tres indicadores
    cols_ind = st.columns(3)
    cols_ind[0].markdown(f"<div style='background:{color_semaforo(c_ndre)}; color:white; padding:5px; text-align:center; border-radius:5px;'>NDRE<br><b>{c_ndre:+.1f}%</b></div>", unsafe_allow_html=True)
    cols_ind[1].markdown(f"<div style='background:{color_semaforo(c_ndmi)}; color:white; padding:5px; text-align:center; border-radius:5px;'>NDMI<br><b>{c_ndmi:+.1f}%</b></div>", unsafe_allow_html=True)
    cols_ind[2].markdown(f"<div style='background:{'#c62828' if abs(d_sar)>2 else '#2e7d32'}; color:white; padding:5px; text-align:center; border-radius:5px;'>Radar<br><b>{'Cambio' if abs(d_sar)>2 else 'Estable'}</b></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Renderizar el Diagnóstico y Recomendación (lo que ya configuramos)
    diagnostico, recomendacion = obtener_diagnostico_y_recomendacion(lote_row)
    color_diag = '#c62828' if "estrés" in diagnostico.lower() or "daño" in diagnostico.lower() else '#2e7d32'
    
    st.markdown(f"""
        <div style='background:{color_diag}; color:white; padding:15px; border-radius:5px;'>
        <b>Diagnóstico:</b> {diagnostico}<br><br>
        <b>Recomendación:</b> {recomendacion}
        </div>
    """, unsafe_allow_html=True)
            with col_der:
                st.markdown("### 🗺️ Visor de Capas")
                capa_sel = st.radio("Capa:", ["Alertas", "NDRE", "NDMI", "Color Real (RGB)"], horizontal=True)
                # ... (todo tu código del Visor de Capas aquí adentro)
                
                # 1. Rutas y variables dinámicas
                ruta_usuario = os.path.join("uploads", st.session_state.get('usuario', ''), str(chacra_sel))
                fecha_buscada = lote_row.get('fecha_optica', '2026-03-29') # Fecha de la pasada seleccionada
                
                # Mapeo de nombres de archivos
                mapa_tipos = {"Alertas": "ALERTAS", "NDRE": "NDRE", "NDMI": "NDMI", "Color Real (RGB)": "RGB"}
                prefijo = mapa_tipos.get(capa_sel, "NDRE")
                
                # 2. Búsqueda dinámica del TIF (basada en prefijo y fecha)
                archivos_disponibles = os.listdir(ruta_usuario) if os.path.exists(ruta_usuario) else []
                nombre_tif = next((f for f in archivos_disponibles if f.startswith(prefijo) and fecha_buscada in f), None)
                path_completo = os.path.join(ruta_usuario, nombre_tif) if nombre_tif else None
                
                # 3. Mapa base
                m = folium.Map(tiles="OpenStreetMap")
                
                # 4. Procesamiento del TIF (Overlay)
                temp_file, bordes = generar_overlay_con_contraste(nombre_tif, capa_sel, ruta_usuario) if nombre_tif else (None, None)
                
                if temp_file and bordes:
                    st.success(f"✅ Cargado: {nombre_tif}")
                    ImageOverlay(image=temp_file, bounds=bordes, opacity=0.7).add_to(m)
                    m.fit_bounds(bordes)
                else:
                    st.warning("⚠️ Imagen no encontrada para esta fecha/capa.")

                # 5. Carga del GeoJSON (Estructura genérica por carpeta)
                path_geojson = os.path.join(ruta_usuario, "LOTES_GEOJSON.geojson")
                if os.path.exists(path_geojson):
                    with open(path_geojson) as f:
                        data = json.load(f)
                    
                    for feature in data['features']:
                        # Asegúrate que 'id_lote' coincida con la propiedad en tu archivo JSON
                        if str(feature['properties'].get('id_lote')) == str(lote_sel):
                            folium.GeoJson(
                                feature,
                                style_function=lambda x: {'color': 'orange', 'weight': 3, 'fillOpacity': 0}
                            ).add_to(m)
                
                st_folium(m, width="100%", height=350, key=f"mapa_lote_{lote_sel}")
                
        else:
            st.warning("No hay datos para esta chacra.")
    else:
        st.error("No hay datos cargados.")


# =====================================================================
# MÓDULO 3: CENTRAL DE REPORTES CORPORATIVOS (FILTRADO Y SEGURO)
# =====================================================================
with tab3:
    st.header("📋 Central de Reportes y Exportación")
    
    # 1. Aplicamos el mismo filtro que en los otros módulos
    # (Usamos df_metricas_usr si ya está definido, o lo recalculamos aquí por seguridad)
    if 'df_metricas_usr' in locals() and not df_metricas_usr.empty:
        df_reporte_base = df_metricas_usr.copy()
    else:
        df_reporte_base = df_metricas.copy() # Fallback

    if not df_reporte_base.empty:
        lista_chacras_r = sorted(list(set(df_reporte_base['id_chacra'].tolist())))
        chacra_sel_r = st.selectbox("🏢 Filtrar Reporte por Establecimiento:", lista_chacras_r, key="sel_chacra_m3_unique_key")
        df_r_filtrado = df_reporte_base[df_reporte_base['id_chacra'] == chacra_sel_r]
        
        if not df_r_filtrado.empty:
            # 2. Métricas de resumen (Solo del filtrado)
            tot_lotes = len(df_r_filtrado)
            lotes_criticos_n = len(df_r_filtrado[df_r_filtrado['porcentaje_alerta'] > 15.0])
            avg_comprometido = df_r_filtrado['porcentaje_alerta'].mean()
            
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Total Lotes", f"{tot_lotes} Lotes")
            col_r2.metric("Críticos (>15%)", f"{lotes_criticos_n} Focos")
            col_r3.metric("Promedio Afectación", f"{avg_comprometido:.1f} %")
            
            st.markdown("---")
            
            # 3. Exportación
            col_exp_izq, col_exp_der = st.columns([1, 1])
            with col_exp_izq:
                st.markdown("### 📄 Reporte PDF Oficial")
                pdf_buffer = exportar_pdf_comercial(df_r_filtrado, chacra_sel_r)
                st.download_button("📥 Descargar Reporte Ejecutivo (.PDF)", pdf_buffer, 
                                   file_name=f"AGIS_Informe_{chacra_sel_r.replace(' ', '_')}.pdf", 
                                   mime="application/pdf", use_container_width=True)
            
            with col_exp_der:
                st.markdown("### 📊 Anexo Técnico")
                pdf_datos_buffer = exportar_pdf_datos_tecnicos(df_r_filtrado, chacra_sel_r)
                st.download_button("📥 Descargar Tabla Datos (.PDF)", pdf_datos_buffer, 
                                   file_name=f"AGIS_Anexo_{chacra_sel_r.replace(' ', '_')}.pdf", 
                                   mime="application/pdf", use_container_width=True)

            # 4. Vista previa de Hoja de Ruta (Misma lógica del Módulo 2)
            st.markdown("---")
            st.markdown("### 📝 Vista Previa de Hojas de Ruta")
            for _, fila in df_r_filtrado.sort_values(by='porcentaje_alerta', ascending=False).iterrows():
                pct = float(fila['porcentaje_alerta'])
                color_borde = "#c62828" if pct > 15.0 else ("#ef6c00" if pct > 2.0 else "#2e7d32")
                alerta_txt = "🚨 CRÍTICO" if pct > 15.0 else ("⚠️ REVISIÓN" if pct > 2.0 else "🟢 ESTABLE")
                
                st.markdown(f"""
                <div class='report-card' style='border-left: 6px solid {color_borde}; padding:10px; background:#f9f9f9; margin-bottom:10px;'>
                    <div style='display: flex; justify-content: space-between;'>
                        <h4 style='margin:0;'>Lote {fila['id_lote_str']} — {str(fila.get('cultivo', 'N/A')).upper()}</h4>
                        <span style='font-weight:bold; color:{color_borde};'>{alerta_txt} ({pct:.1f}%)</span>
                    </div>
                </div>""", unsafe_allow_html=True)
    else:
        st.warning("No hay datos disponibles para generar reportes.")
# =====================================================================
# MÓDULO 4: MI PERFIL (GESTIÓN DE CUENTA PERSONAL)
# =====================================================================
with tab4:
    st.header("👤 Mi Perfil de Usuario")
    st.write(f"Usuario activo: **{st.session_state['usuario']}**")
    
    st.divider()
    st.subheader("🔑 Cambiar mi contraseña")
    
    with st.form("form_cambiar_pass"):
        pass_actual = st.text_input("Contraseña actual", type="password")
        pass_nueva = st.text_input("Nueva contraseña", type="password")
        pass_confirm = st.text_input("Confirmar nueva contraseña", type="password")
        btn_cambiar = st.form_submit_button("Actualizar contraseña")
        
        if btn_cambiar:
            if pass_nueva == pass_confirm: # Asegura esta sangría
                conn = sqlite3.connect("database/agis_database.db")
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM usuarios WHERE username = ?", (st.session_state['usuario'],))
                resultado = cursor.fetchone()
                
                hash_actual_input = hashlib.sha256(pass_actual.encode()).hexdigest()
                
                if resultado and resultado[0] == hash_actual_input:
                    hash_nueva = hashlib.sha256(pass_nueva.encode()).hexdigest()
                    cursor.execute("UPDATE usuarios SET password = ? WHERE username = ?", (hash_nueva, st.session_state['usuario']))
                    conn.commit()
                    st.success("¡Contraseña actualizada con éxito!")
                else:
                    st.error("La contraseña actual es incorrecta.")
                conn.close()
            else: # <--- FALTABA ESTO
                st.error("Las contraseñas nuevas no coinciden.")

# =====================================================================
# MÓDULO 5: AGIS STUDIO (CENTRO DE CONTROL ADMINISTRATIVO)
# =====================================================================

with tab5:
    st.header("💻 AGIS Studio: Centro de Control")
    st.info("Panel exclusivo para administración de usuarios y carga de datos.")
    
    sub_tab1, sub_tab2 = st.tabs(["👥 Gestión de Usuarios", "📂 Carga de Datos en Línea"])
    
    # --- SUB-TAB 1: GESTIÓN DE USUARIOS ---
    with sub_tab1:
        st.subheader("👥 Gestión de Usuarios")
        
        # Formulario para registrar nuevo usuario
        with st.expander("➕ Registrar Nuevo Usuario"):
            with st.form("form_usuario", clear_on_submit=True):
                nombre_usuario = st.text_input("Nombre y Apellido")
                user_login = st.text_input("Nombre de Usuario (Login)")
                pass_usuario = st.text_input("Contraseña", type="password")
                email_usuario = st.text_input("Email")
                telefono_usuario = st.text_input("WhatsApp (+549...)", placeholder="+549...")
                perfil_usuario = st.selectbox("Perfil", ["Productor", "Técnico", "Administrador"])
                chacras_asignadas = st.text_area("Chacras asignadas (separadas por coma)")
                btn_guardar_usuario = st.form_submit_button("Guardar Usuario")
                
            if btn_guardar_usuario:
                if nombre_usuario and user_login and pass_usuario:
                    try:
                        hash_pass = hashlib.sha256(pass_usuario.encode()).hexdigest()
                        conn = sqlite3.connect("database/agis_database.db")
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO usuarios (nombre, username, password, email, telefono, perfil, chacras)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (nombre_usuario, user_login, hash_pass, email_usuario, telefono_usuario, perfil_usuario, chacras_asignadas))
                        conn.commit()
                        conn.close()
                        st.success(f"Usuario {nombre_usuario} registrado.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Error: El usuario ya existe.")
                else:
                    st.error("Campos obligatorios incompletos.")

        st.divider()
        st.subheader("📋 Usuarios Registrados")
        
        # Obtener lista actualizada
        conn = sqlite3.connect("database/agis_database.db")
        df_usuarios = pd.read_sql_query("SELECT id, nombre, username, perfil FROM usuarios", conn)
        conn.close()

        # Mostrar tabla interactiva con acciones
        for index, row in df_usuarios.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{row['username']}** ({row['perfil']}) - {row['nombre']}")
            
            # Acción: Eliminar
            if c2.button("🗑️ Eliminar", key=f"del_{row['id']}"):
                conn = sqlite3.connect("database/agis_database.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM usuarios WHERE id = ?", (row['id'],))
                conn.commit()
                conn.close()
                st.rerun()
                
            # Acción: Editar
            if c3.button("✏️ Editar", key=f"edit_{row['id']}"):
                st.session_state[f"edit_mode_{row['id']}"] = True

            # Formulario de edición (solo aparece si se presiona editar)
            if st.session_state.get(f"edit_mode_{row['id']}", False):
                with st.form(key=f"form_edit_{row['id']}"):
                    nuevo_nombre = st.text_input("Nuevo Nombre", value=row['nombre'])
                    btn_confirmar = st.form_submit_button("Guardar Cambios")
                    if btn_confirmar:
                        conn = sqlite3.connect("database/agis_database.db")
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET nombre = ? WHERE id = ?", (nuevo_nombre, row['id']))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_mode_{row['id']}"] = False
                        st.rerun()

    # --- SUB-TAB 2: CARGA DE DATOS EN LÍNEA ---
    with sub_tab2:
        st.subheader("📂 Carga de Datos Semanales")
        conn = sqlite3.connect("database/agis_database.db")
        nombres_usuarios = pd.read_sql_query("SELECT username FROM usuarios", conn)['username'].tolist()
        conn.close()
        
        user_sel = st.selectbox("Seleccionar Cliente:", nombres_usuarios, key="sel_user_carga")
        chacra_sel = st.text_input("Nombre de la Chacra:", key="in_chacra_carga")
        archivos = st.file_uploader(
    "Subir Archivos (CSV, TIF, GeoJSON)", 
    type=['csv', 'tif', 'json', 'geojson'], 
    accept_multiple_files=True,  # <--- ESTO PERMITE SUBIR VARIOS
    key="uploader_archivos"
)
        
        if st.button("Procesar y Asignar"):
            if user_sel and chacra_sel and archivos:
                ruta_dir = os.path.join("uploads", user_sel, chacra_sel)
                os.makedirs(ruta_dir, exist_ok=True)
                
                # Iteramos sobre cada archivo subido
                for archivo in archivos:
                    ruta_archivo = os.path.join(ruta_dir, archivo.name)
                    with open(ruta_archivo, "wb") as f:
                        f.write(archivo.getbuffer())
                
                st.success(f"Se han guardado {len(archivos)} archivos correctamente para {user_sel}.")
                st.balloons()
            else:
                st.error("Por favor completa el cliente, chacra y selecciona al menos un archivo.")
