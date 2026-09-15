import streamlit as st
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from streamlit_js_eval import get_geolocation
import pydeck as pdk
import os

# --- 1. CONFIGURACIÓN Y ESTILOS HUD ---
st.set_page_config(page_title="PROP-SCAN HBU SCOUT", layout="wide", initial_sidebar_state="collapsed")

if "location" not in st.session_state:
    st.session_state.location = None

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono:wght@500;800&display=swap');

    .stApp { background-color: #08090C; color: #FFFFFF; font-family: 'Inter', sans-serif; }

    .hud-panel {
        background: rgba(18, 20, 26, 0.85);
        border: 1px solid rgba(255, 95, 31, 0.2);
        padding: 16px;
        border-radius: 10px;
        backdrop-filter: blur(12px);
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.7);
    }

    .dial-container { display: flex; justify-content: center; align-items: center; padding: 5px 0; }

    .central-dial {
        width: 230px; height: 230px;
        border: 5px solid #FF5F1F;
        border-radius: 50%;
        display: flex; flex-direction: column;
        justify-content: center; align-items: center;
        background: radial-gradient(circle, rgba(255, 95, 31, 0.15) 0%, rgba(10, 10, 15, 0.9) 80%);
        box-shadow: 0 0 35px rgba(255, 95, 31, 0.4);
    }

    .dial-header { color: #888; font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase; }
    .dial-value { color: #FFF; font-size: 2.2rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
    .dial-sub { color: #00E676; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; text-align: center; padding: 0 8px; }

    .stButton>button {
        background: linear-gradient(90deg, #FF5F1F 0%, #E64A19 100%) !important;
        color: white !important;
        border: none !important;
        width: 100%; height: 48px;
        font-weight: 800; font-size: 0.95rem;
        letter-spacing: 2px; border-radius: 6px;
        text-transform: uppercase;
        box-shadow: 0 4px 15px rgba(255, 95, 31, 0.35);
    }

    .status-pill {
        background: #00E676; color: #000; padding: 2px 8px;
        border-radius: 4px; font-weight: 800; font-size: 0.65rem;
        text-transform: uppercase;
    }

    .poi-badge {
        display: inline-block; padding: 2px 6px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    }

    [data-testid="stMetricValue"] { color: #FF5F1F !important; font-family: 'JetBrains Mono', monospace; font-size: 1.35rem !important; }
    [data-testid="stMetricLabel"] { color: #888 !important; font-weight: 600; text-transform: uppercase; font-size: 0.72rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTORES ESPACIALES EN MEMORIA (KDTree Dual) ---
@st.cache_resource
def load_engines():
    base_dir = os.path.dirname(__file__)

    # 1. Motor de Manzanas HBU
    path_mza = os.path.join(base_dir, 'data', 'master_jalisco_hbu_scout.parquet')
    if not os.path.exists(path_mza): path_mza = 'master_jalisco_hbu_scout.parquet'
    df_mza = pd.read_parquet(path_mza)
    tree_mza = KDTree(df_mza[['lat_centroide', 'lon_centroide']].values)

    # 2. Motor de Comercios DENUE
    path_poi = os.path.join(base_dir, 'data', 'jalisco_denue_scout.parquet')
    if not os.path.exists(path_poi): path_poi = 'jalisco_denue_scout.parquet'
    df_poi = pd.read_parquet(path_poi)
    tree_poi = KDTree(df_poi[['latitud', 'longitud']].values)

    return df_mza, tree_mza, df_poi, tree_poi

# Paleta Semántica de Colores RGBA para POIs en PyDeck
COLOR_MAP = {
    'Retail ancla':    [255, 140, 0, 240],   # Naranja fuerte
    'Salud':           [255, 50, 50, 240],    # Rojo neón
    'Educacion':       [0, 180, 255, 240],   # Azul eléctrico
    'Financiero':      [255, 215, 0, 240],   # Amarillo oro
    'Gastronomia':     [0, 230, 118, 240],   # Verde esmeralda
    'Ocio':            [180, 0, 255, 240],   # Púrpura
    'Comercio basico': [160, 160, 160, 200], # Gris claro
    'OFFICE_SERVICES': [0, 255, 255, 240]    # Cian
}

def decimal_to_dms(deg, is_lat=True):
    direction = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    deg = abs(deg)
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m/60) * 3600, 2)
    return f"{direction} {d}°{m:02d}'{s:05.2f}\""

# --- 3. INTERFAZ PRINCIPAL ---
def main():
    st.markdown("<p style='text-align:center; color:#FF5F1F; letter-spacing:4px; margin-bottom:0; font-weight:800; font-size:1.3rem;'>PROP-SCAN HBU SCOUT & RADAR</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#666; font-size:0.78rem; margin-top:2px;'>SISTEMA TÁCTICO DE ADQUISICIÓN DE TERRENOS | JALISCO</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:8px auto; width:30%; opacity:0.15;'>", unsafe_allow_html=True)

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

        df_mza, tree_mza, df_poi, tree_poi = load_engines()

        # 1. Búsqueda de Manzana (KDTree 1)
        dist_deg, idx_mza = tree_mza.query(np.array([lat_now, lon_now]))
        data = df_mza.iloc[idx_mza]
        dist_m = dist_deg * 111139

        # 2. Búsqueda de POIs Cercanos (KDTree 2 por Radio: 800m)
        radio_deg = 800.0 / 111139.0
        poi_indices = tree_poi.query_ball_point([lat_now, lon_now], r=radio_deg)

        # Si hay menos de 5 comercios en 800m, buscar los 5 más próximos sin límite de distancia
        if len(poi_indices) < 5:
            _, poi_indices = tree_poi.query([lat_now, lon_now], k=min(10, len(df_poi)))
            if isinstance(poi_indices, np.int64): poi_indices = [poi_indices]

        nearby_pois = df_poi.iloc[poi_indices].copy()

        # Calcular distancia exacta a cada POI
        d_lats = nearby_pois['latitud'].values - lat_now
        d_lons = (nearby_pois['longitud'].values - lon_now) * np.cos(np.radians(lat_now))
        nearby_pois['dist_m'] = np.sqrt(d_lats**2 + d_lons**2) * 111139
        nearby_pois = nearby_pois.sort_values(by='dist_m').head(25)  # Guardar los 25 más cercanos

        # --- SECCIÓN SUPERIOR: TELEMETRÍA Y DIAL CENTRAL ---
        col_izq, col_cen, col_der = st.columns([1, 1.2, 1])

        with col_izq:
            st.markdown(f"""
                <div class="hud-panel">
                    <p style="color:#888; font-size:0.75rem; margin:0;">TELEMETRÍA SATELITAL</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
                        <span style="color:#00E676; font-weight:bold; font-size:0.9rem;">RADAR ACTIVO</span>
                        <span class="status-pill">GPS OK</span>
                    </div>
                    <hr style="opacity:0.1; margin:8px 0;">
                    <p style="color:#888; font-size:0.75rem; margin:0;">PRECISIÓN GPS</p>
                    <p style="font-family:monospace; margin:0; font-size:1rem; color:#FF5F1F;">{acc_now:.1f} m</p>
                    <p style="color:#888; font-size:0.75rem; margin-top:6px;">POIs EN 800M</p>
                    <p style="font-family:monospace; margin:0; font-size:1rem; color:#00E676;">{len(nearby_pois)} Detectados</p>
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
                    <p style="color:#888; font-size:0.75rem; margin:0;">IDENTIFICACIÓN PREDIO</p>
                    <p style="color:#FFF; font-weight:bold; margin:2px 0 0 0; font-size:0.88rem;">{data.get('NOM_MUN', 'JALISCO')}</p>
                    <hr style="opacity:0.1; margin:8px 0;">
                    <p style="color:#888; font-size:0.75rem; margin:0;">CLAVE MANZANA (16 DÍGITOS)</p>
                    <p style="font-family:monospace; margin:0; font-size:0.82rem; color:#FF5F1F;">{data.get('cvegeo_mza', 'S/D')}</p>
                    <p style="color:#888; font-size:0.75rem; margin-top:6px;">COORDENADA GEODÉSICA</p>
                    <p style="font-family:monospace; margin:0; font-size:0.78rem; color:#AAA;">{decimal_to_dms(lat_now, True)}</p>
                    <p style="font-family:monospace; margin:0; font-size:0.78rem; color:#AAA;">{decimal_to_dms(lon_now, False)}</p>
                </div>
            """, unsafe_allow_html=True)

        # --- SECCIÓN MEDIA: PANELES DE INTELIGENCIA DE NEGOCIO ---
        r_col1, r_col2 = st.columns(2)

        with r_col1:
            st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
            st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px; margin-bottom:8px;'>⚖️ POTENCIAL LEGAL Y NORMATIVO</p>", unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("Zonificación", f"{data.get('tipo_uso', 'S/D')}")
            m2.metric("Niveles Máx", f"{int(data.get('altura_max', 0))} Pisos")

            m3, m4 = st.columns(2)
            cus_val = data.get('cus', 0.0)
            cos_val = data.get('cos', 0.0)
            m3.metric("CUS (Factor Terreno)", f"{cus_val:.2f}")
            m4.metric("COS (% Desplante)", f"{cos_val*100:.0f}%")

            m5, m6 = st.columns(2)
            m2_const = data.get('m2_construccion_max', 0.0)
            viv_max = data.get('potencial_viviendas_max', 0.0)
            m5.metric("M² Construibles Estimados", f"{m2_const:,.0f} m²")
            m6.metric("Capacidad Habitacional", f"{viv_max:,.0f} Viv")
            st.markdown('</div>', unsafe_allow_html=True)

        with r_col2:
            st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
            st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px; margin-bottom:8px;'>📈 DEMANDA Y ENTORNO H3</p>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("Poder Adquisitivo (NSE)", f"{data.get('nse_score', 0.0):.1f} / 100")
            c2.metric("Amenity Score H3", f"{data.get('amenity_score', 0.0):.1f} / 100")

            c3, c4 = st.columns(2)
            c3.metric("Población en Manzana", f"{int(data.get('POBTOT', 0))} hab")
            c4.metric("Escolaridad Media", f"{data.get('GRAPROES', 0.0):.1f} Años")

            c5, c6 = st.columns(2)
            pct_int = data.get('pct_internet', 0.0) * 100
            pct_aut = data.get('pct_auto', 0.0) * 100
            c5.metric("Penetración Internet", f"{pct_int:.0f}%")
            c6.metric("Tasa de Vehículos", f"{pct_aut:.0f}%")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- SECCIÓN INFERIOR: MAPA TÁCTICO PYDECK CON PUNTOS DENUE ---
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="color:#FF5F1F; font-weight:bold; letter-spacing:1px; font-size:0.88rem;'>🗺️ RADAR ESPACIAL: PRECIO, PREDIO Y AMENIDADES DENUE</span>
                <span style="color:#888; font-size:0.75rem; font-family:monospace;">RADIO: 800M</span>
            </div>
        """, unsafe_allow_html=True)

        node_lat = float(data['lat_centroide'])
        node_lon = float(data['lon_centroide'])
        u_lat = float(lat_now)
        u_lon = float(lon_now)

        # 1. Puntos de Usuario y Predio
        base_points = pd.DataFrame([
            {"name": "Posición Scout (GPS)", "lat": u_lat, "lon": u_lon, "color": [0, 230, 118, 255], "radius": 14},
            {"name": "Centroide Predio HBU", "lat": node_lat, "lon": node_lon, "color": [255, 95, 31, 255], "radius": 20}
        ])

        # 2. Línea de conexión al predio
        line_data = pd.DataFrame([{"start": [u_lon, u_lat], "end": [node_lon, node_lat]}])

        # 3. Capa de POIs DENUE con color semántico
        # LÍNEA CORREGIDA:

        nearby_pois['color'] = [COLOR_MAP.get(str(cat), [200, 200, 200, 200]) for cat in nearby_pois['cat_hbu']]

        view_state = pdk.ViewState(
            latitude=(u_lat + node_lat) / 2,
            longitude=(u_lon + node_lon) / 2,
            zoom=15,
            pitch=35
        )

        layers = [
            # Puntos DENUE por Categoría
            pdk.Layer(
                "ScatterplotLayer",
                nearby_pois,
                get_position=["longitud", "latitud"],
                get_color="color",
                get_radius="radius",
                radius_min_pixels=5,
                radius_max_pixels=12,
                pickable=True
            ),
            # Línea al predio
            pdk.Layer(
                "LineLayer",
                line_data,
                get_source_position="start",
                get_target_position="end",
                get_color=[255, 95, 31, 220],
                get_width=3
            ),
            # Scout y Predio
            pdk.Layer(
                "ScatterplotLayer",
                base_points,
                get_position=["lon", "lat"],
                get_color="color",
                get_radius="radius",
                pickable=True
            )
        ]

        st.pydeck_chart(
            pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
                tooltip={"html": "<b>{nom_estab}</b><br/>{cat_hbu}<br/>{name}", "style": {"color": "white", "backgroundColor": "#111"}}
            ),
            use_container_width=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # --- SECCIÓN DE NEGOCIOS EN WALKING DISTANCE ---
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown("<p style='color:#FF5F1F; font-weight:bold; letter-spacing:1px; margin-bottom:8px;'>🏬 RADAR DE NEGOCIOS CERCANOS (TOP PROXIMIDAD A PIE)</p>", unsafe_allow_html=True)

        if not nearby_pois.empty:
            cols_show = nearby_pois[['cat_hbu', 'nom_estab', 'dist_m']].head(8).copy()
            cols_show.columns = ['Categoría', 'Establecimiento', 'Distancia (Metros)']
            cols_show['Distancia (Metros)'] = cols_show['Distancia (Metros)'].apply(lambda x: f"{x:.0f} m ({x/80:.1f} min)")
            st.dataframe(cols_show, use_container_width=True, hide_index=True)
        else:
            st.caption("No se detectaron comercios ancla registrados en un radio de 800 metros.")
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
