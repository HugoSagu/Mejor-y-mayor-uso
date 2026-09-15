import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import get_geolocation
import pydeck as pdk
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PROP-SCAN HBU SCOUT", layout="wide", initial_sidebar_state="collapsed")

if "location" not in st.session_state:
    st.session_state.location = None

# Estilo Táctico Dark HUD
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono:wght@500;800&display=swap');

    .stApp {
        background-color: #08090C;
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
    }

    .hud-panel {
        background: rgba(18, 20, 26, 0.85);
        border: 1px solid rgba(255, 95, 31, 0.2);
        padding: 18px;
        border-radius: 10px;
        backdrop-filter: blur(12px);
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.7);
    }

    .dial-container {
        display: flex; justify-content: center; align-items: center; padding: 10px 0;
    }

    .central-dial {
        width: 240px; height: 240px;
        border: 5px solid #FF5F1F;
        border-radius: 50%;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center;
        background: radial-gradient(circle, rgba(255, 95, 31, 0.15) 0%, rgba(10, 10, 15, 0.9) 80%);
        box-shadow: 0 0 35px rgba(255, 95, 31, 0.4);
    }

    .dial-header { color: #888; font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase; }
    .dial-value { color: #FFF; font-size: 2.2rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
    .dial-sub { color: #00E676; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; text-align: center; padding: 0 10px; }

    .stButton>button {
        background: linear-gradient(90deg, #FF5F1F 0%, #E64A19 100%) !important;
        color: white !important;
        border: none !important;
        width: 100%;
        height: 50px;
        font-weight: 800;
        font-size: 1rem;
        letter-spacing: 2px;
        border-radius: 6px;
        text-transform: uppercase;
        box-shadow: 0 4px 15px rgba(255, 95, 31, 0.35);
    }

    .status-pill {
        background: #00E676; color: #000; padding: 2px 8px;
        border-radius: 4px; font-weight: 800; font-size: 0.65rem;
        text-transform: uppercase;
    }

    [data-testid="stMetricValue"] { color: #FF5F1F !important; font-family: 'JetBrains Mono', monospace; font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { color: #888 !important; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# 2. MOTOR ESPACIAL EN MEMORIA (KDTree)
@st.cache_resource
def load_spatial_engine():
    # Ruta relativa al repositorio en GitHub
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'master_jalisco_hbu_scout.parquet')
    if not os.path.exists(data_path):
        # Fallback si se ejecuta en raíz
        data_path = 'master_jalisco_hbu_scout.parquet'
    
    df = pd.read_parquet(data_path)
    coords = df[['lat_centroide', 'lon_centroide']].values
    tree = KDTree(coords)
    return df, tree

def decimal_to_dms(deg, is_lat=True):
    direction = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m/60) * 3600, 2)
    return f"{direction} {d}°{m:02d}'{s:05.2f}\""

# 3. INTERFAZ PRINCIPAL
def main():
    st.markdown("<p style='text-align:center; color:#FF5F1F; letter-spacing:4px; margin-bottom:0; font-weight:800; font-size:1.4rem;'>PROP-SCAN HBU SCOUT</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#666; font-size:0.8rem; margin-top:2px;'>SISTEMA TÁCTICO DE EXPLORACIÓN DE TERRENOS | JALISCO</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:10px auto; width:30%; opacity:0.15;'>", unsafe_allow_html=True)

    # GPS o Selección Manual
    if st.button("🔄 SINCRONIZAR SENSOR GPS DE CAMPO"):
        st.session_state.location = None
        st.rerun()

    if st.session_state.location is None:
        loc = get_geolocation()
        if loc and 'coords' in loc:
            st.session_state.location = {
                "lat": loc['coords']['latitude'],
                "lon": loc['coords']['longitude'],
                "acc": loc['coords'].get('accuracy', 1.0)
            }
            st.rerun()
        else:
            with st.expander("⌨️ Ingreso Manual de Coordenadas (Modo Escritorio)"):
                c1, c2 = st.columns(2)
                m_lat = c1.number_input("Latitud", value=20.6950, format="%.6f")
                m_lon = c2.number_input("Longitud", value=-103.3850, format="%.6f")
                if st.button("FIJAR COORDENADA"):
                    st.session_state.location = {"lat": m_lat, "lon": m_lon, "acc": 0.0}
                    st.rerun()

    if st.session_state.location:
        lat_now = st.session_state.location['lat']
        lon_now = st.session_state.location['lon']
        acc_now = st.session_state.location.get('acc', 1.0)

        df, tree = load_spatial_engine()

        # Búsqueda KDTree en submilisegundos
        dist_deg, idx = tree.query(np.array([lat_now, lon_now]))
        data = df.iloc[idx]
        dist_m = dist_deg * 111139

        col_izq, col_cen, col_der = st.columns([1, 1.2, 1])

        with col_izq:
            st.markdown(f"""
                <div class="hud-panel">
                    <p style="color:#888; font-size:0.75rem; margin:0;">TELEMETRÍA SATELITAL</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
                        <span style="color:#00E676; font-weight:bold; font-size:0.9rem;">ENLACE ACTIVO</span>
                        <span class="status-pill">GPS OK</span>
                    </div>
                    <hr style="opacity:0.1; margin:10px 0;">
                    <p style="color:#888; font-size:0.75rem; margin:0;">PRECISIÓN ESTIMADA</p>
                    <p style="font-family:monospace; margin:0; font-size:1.1rem; color:#FF5F1F;">{acc_now:.1f} m</p>
                    <p style="color:#888; font-size:0.75rem; margin-top:8px;">DISTANCIA AL CENTROIDE</p>
                    <p style="font-family:monospace; margin:0; font-size:1rem; color:#FFF;">{dist_m:.0f} m</p>
                </div>
            """, unsafe_allow_html=True)

        with col_cen:
            opp_score = data.get('hbu_opportunity_score', 0.0)
            hbu_label = data.get('hbu_label', 'EVALUANDO')
            st.markdown(f"""
                <div class="dial-container">
                    <div class="central-dial">
                        <span class="dial-header">HBU OPPORTUNITY</span>
                        <span class="dial-value">{opp_score:.1f}</span>
                        <span class="dial-sub">{hbu_label}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col_der:
            st.markdown(f"""
                <div class="hud-panel">
                    <p style="color:#888; font-size:0.75rem; margin:0;">IDENTIFICACIÓN CATASTRAL</p>
                    <p style="color:#FFF; font-weight:bold; margin:2px 0 0 0; font-size:0.9rem;">{data.get('NOM_MUN', 'JALISCO')}</p>
                    <hr style="opacity:0.1; margin:10px 0;">
                    <p style="color:#888; font-size:0.75rem; margin:0;">CLAVE MANZANA (16 DÍGITOS)</p>
                    <p style="font-family:monospace; margin:0; font-size:0.85rem; color:#FF5F1F;">{data.get('cvegeo_mza', 'S/D')}</p>
                    <p style="color:#888; font-size:0.75rem; margin-top:8px;">COORDENADA GEODÉSICA</p>
                    <p style="font-family:monospace; margin:0; font-size:0.8rem; color:#AAA;">{decimal_to_dms(lat_now, True)}</p>
                    <p style="font-family:monospace; margin:0; font-size:0.8rem; color:#AAA;">{decimal_to_dms(lon_now, False)}</p>
                </div>
            """, unsafe_allow_html=True)

        # Paneles de Métricas
        r_col1, r_col2 = st.columns(2)

        with r_col1:
            st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
            st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px; margin-bottom:10px;'>⚖️ POTENCIAL NORMATIVO Y LEGAL</p>", unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("Zonificación", f"{data.get('tipo_uso', 'S/D')}")
            m2.metric("Niveles Permitidos", f"{int(data.get('altura_max', 0))} Pisos")

            m3, m4 = st.columns(2)
            cus_val = data.get('cus', 0.0)
            cos_val = data.get('cos', 0.0)
            m3.metric("CUS (Veces Terreno)", f"{cus_val:.2f}")
            m4.metric("COS (% Desplante)", f"{cos_val*100:.0f}%")

            m5, m6 = st.columns(2)
            m2_const = data.get('m2_construccion_max', 0.0)
            viv_max = data.get('potencial_viviendas_max', 0.0)
            m5.metric("M² Construibles Estimados", f"{m2_const:,.0f} m²")
            m6.metric("Densidad Estimada", f"{viv_max:,.0f} Viv")
            st.markdown('</div>', unsafe_allow_html=True)

        with r_col2:
            st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
            st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px; margin-bottom:10px;'>📈 DEMANDA SOCIOECONÓMICA Y ENTORNO</p>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Poder Adquisitivo (NSE)", f"{data.get('nse_score', 0.0):.1f} / 100")
            c2.metric("Amenidades H3 (300m)", f"{data.get('amenity_score', 0.0):.1f} / 100")

            c3, c4 = st.columns(2)
            c3.metric("Población en Manzana", f"{int(data.get('POBTOT', 0))} hab")
            c4.metric("Escolaridad Promedio", f"{data.get('GRAPROES', 0.0):.1f} Años")

            c5, c6 = st.columns(2)
            pct_int = data.get('pct_internet', 0.0) * 100
            pct_aut = data.get('pct_auto', 0.0) * 100
            c5.metric("Penetración Internet", f"{pct_int:.0f}%")
            c6.metric("Tasa de Automóviles", f"{pct_aut:.0f}%")
            st.markdown('</div>', unsafe_allow_html=True)

        # Mapa Táctico PyDeck
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="color:#FF5F1F; font-weight:bold; letter-spacing:1px; font-size:0.9rem;'>🗺️ VERIFICACIÓN ESPACIAL TÁCTICA</span>
                <span style="color:#888; font-size:0.75rem; font-family:monospace;">VECTOR SCOUT-PREDIO: {dist_m:.1f} M</span>
            </div>
        """, unsafe_allow_html=True)

        node_lat = float(data['lat_centroide'])
        node_lon = float(data['lon_centroide'])
        u_lat = float(lat_now)
        u_lon = float(lon_now)

        map_data = pd.DataFrame([
            {"name": "Posición Scout (GPS)", "lat": u_lat, "lon": u_lon, "color": [0, 230, 118, 255], "radius": 15},
            {"name": "Centroide Predio HBU", "lat": node_lat, "lon": node_lon, "color": [255, 95, 31, 255], "radius": 22}
        ])

        line_data = pd.DataFrame([{"start": [u_lon, u_lat], "end": [node_lon, node_lat]}])

        view_state = pdk.ViewState(
            latitude=(u_lat + node_lat) / 2,
            longitude=(u_lon + node_lon) / 2,
            zoom=16,
            pitch=30
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[
                    pdk.Layer("ScatterplotLayer", map_data, get_position=["lon", "lat"], get_color="color", get_radius="radius", pickable=True),
                    pdk.Layer("LineLayer", line_data, get_source_position="start", get_target_position="end", get_color=[255, 95, 31, 200], get_width=3)
                ],
                initial_view_state=view_state,
                map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
                tooltip={"text": "{name}"}
            ),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
