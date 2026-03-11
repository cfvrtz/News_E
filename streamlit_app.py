"""
streamlit_app.py — Dashboard de noticias del sector eléctrico chileno.
Lee el JSON generado por el pipeline desde GitHub Releases.
"""

import streamlit as st
import requests
import json
from datetime import datetime

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────────

# Cambia esto por tu usuario y repo de GitHub
GITHUB_USER = "cfvrtz"
GITHUB_REPO = "News_E"
JSON_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/latest-news/noticias.json"

CATEGORY_COLORS = {
    "Transmisión":         "#f5c518",
    "Generación & BESS":   "#4ade80",
    "Regulación":          "#60a5fa",
    "Mercado & Contratos": "#c084fc",
    "Combustibles & Gas":  "#f97316",
    "Institucional":       "#fb7185",
}

SOURCE_ICONS = {
    "Coordinador Eléctrico": "⚡",
    "Panorama Energético":   "🔆",
    "Diario Financiero":     "📊",
    "Electrominería":        "⛏️",
    "CNE":                   "📋",
    "SEC":                   "🔍",
    "Ministerio de Energía": "🏛️",
    "Diario Oficial":        "📜",
    "El Mercurio":           "📰",
    "Pulso":                 "📈",
    "Energía Estratégica":   "🔋",
    "Revista Electricidad":  "⚙️",
    "CEN Clipper":           "📡",
}

# ── ESTILOS ────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Monitor Eléctrico Chile",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #080d1a;
    color: #e2e8f0;
}

.stApp { background-color: #080d1a; }

/* Header */
.header-container {
    background: linear-gradient(180deg, #0d1528 0%, #080d1a 100%);
    border-bottom: 1px solid rgba(245,197,24,0.15);
    padding: 28px 0 20px;
    margin-bottom: 24px;
}
.header-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(245,197,24,0.1);
    border: 1px solid rgba(245,197,24,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 600;
    color: #f5c518;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.header-title {
    font-family: 'Playfair Display', serif;
    font-size: 38px;
    font-weight: 900;
    color: #f1f5f9;
    line-height: 1.1;
    letter-spacing: -0.02em;
    margin: 0 0 6px;
}
.header-accent { color: #f5c518; }
.header-sub {
    color: #64748b;
    font-size: 14px;
    margin: 0;
}

/* Cards */
.news-card {
    background: #0d1528;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
    transition: all 0.2s;
}
.news-card:hover {
    border-color: rgba(245,197,24,0.18);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}
.card-top-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
}
.card-badges {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    margin-top: 6px;
}
.cat-badge {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-radius: 6px;
    padding: 3px 9px;
}
.rel-badge {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-radius: 6px;
    padding: 3px 9px;
}
.card-title {
    font-family: 'Playfair Display', serif;
    font-size: 16px;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.35;
    margin-bottom: 10px;
}
.card-summary {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.6;
    margin-bottom: 14px;
}
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255,255,255,0.05);
    padding-top: 10px;
    font-size: 11px;
    color: #475569;
}
.card-source { display: flex; align-items: center; gap: 5px; }

/* Stats bar */
.stats-bar {
    background: #0d1528;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
    display: flex;
    gap: 28px;
    flex-wrap: wrap;
    align-items: center;
}
.stat-item { display: flex; gap: 6px; align-items: baseline; }
.stat-num {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 700;
}
.stat-label { font-size: 11px; color: #475569; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1528 !important;
    border-right: 1px solid rgba(245,197,24,0.1);
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* Filtros */
.filter-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #f5c518;
    margin-bottom: 8px;
}

/* Ocultar elementos de Streamlit */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ── CARGA DE DATOS ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)  # cachea 5 minutos
def cargar_noticias():
    try:
        r = requests.get(JSON_URL, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "noticias": [], "fecha_actualizacion": None}


def get_source_icon(fuente):
    if not fuente:
        return "📡"
    for k, v in SOURCE_ICONS.items():
        if k.lower() in fuente.lower():
            return v
    return "📡"


def render_card(n):
    cat = n.get("categoria", "General")
    color = CATEGORY_COLORS.get(cat, "#94a3b8")
    rel = n.get("relevancia", "media")
    fuente = n.get("fuente", "")
    fecha = n.get("fecha") or "—"
    titulo = n.get("titulo", "")
    resumen = n.get("resumen") or ""
    url = n.get("url")
    icon = get_source_icon(fuente)

    rel_color = "#f5c518" if rel == "alta" else "#64748b"
    rel_bg = "rgba(245,197,24,0.08)" if rel == "alta" else "transparent"
    rel_border = "rgba(245,197,24,0.2)" if rel == "alta" else "rgba(255,255,255,0.06)"
    rel_label = "★ Alta" if rel == "alta" else "Media"

    link_html = ""
    if url:
        link_html = f'<a href="{url}" target="_blank" style="color:#60a5fa;font-size:12px;text-decoration:none;">🔗 Ver fuente →</a>'

    html = f"""
    <div class="news-card">
        <div class="card-top-bar" style="background:{color};opacity:0.7;"></div>
        <div class="card-badges">
            <span class="cat-badge" style="color:{color};background:{color}20;border:1px solid {color}30;">
                {cat}
            </span>
            <span class="rel-badge" style="color:{rel_color};background:{rel_bg};border:1px solid {rel_border};">
                {rel_label}
            </span>
        </div>
        <div class="card-title">{titulo}</div>
        <div class="card-summary">{resumen}</div>
        {link_html}
        <div class="card-footer">
            <span class="card-source">{icon} {fuente}</span>
            <span>{fecha}</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ── HEADER ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="header-container">
    <div class="header-badge">⚡ Monitor Energético</div>
    <div class="header-title">Sector Eléctrico<br><span class="header-accent">Chile</span></div>
    <div class="header-sub">Noticias recientes · Transmisión, generación, regulación y mercado</div>
</div>
""", unsafe_allow_html=True)


# ── CARGA ──────────────────────────────────────────────────────────────────────

col_refresh, col_meta = st.columns([1, 4])
with col_refresh:
    if st.button("⟳ Actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data = cargar_noticias()

if "error" in data and data["error"]:
    st.error(f"⚠️ No se pudo cargar el JSON: {data['error']}")
    st.info("Asegúrate de que el pipeline haya corrido al menos una vez y el release 'latest-news' exista en el repo.")
    st.stop()

noticias = data.get("noticias", [])
fecha_act = data.get("fecha_actualizacion", "—")
total_rev = data.get("total_revisadas", "—")
estado = data.get("estado", "ok")

with col_meta:
    cols_meta = st.columns(4)
    cols_meta[0].markdown(f"🟢 **Actualizado:** {fecha_act}")
    cols_meta[1].markdown(f"📰 **{len(noticias)}** noticias seleccionadas")
    cols_meta[2].markdown(f"🔍 **{total_rev}** titulares revisados")
    cols_meta[3].markdown(f"🎯 **{sum(1 for n in noticias if n.get('relevancia')=='alta')}** alta relevancia")

if estado == "fallback":
    st.warning(f"⚠️ Claude no pudo procesar: {data.get('motivo', '')} — mostrando titulares sin resumir.")

if not noticias:
    st.markdown("""
    <div style="text-align:center;padding:80px 0;">
        <div style="font-size:48px;margin-bottom:16px;">⚡</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;color:#f1f5f9;margin-bottom:10px;">
            Sin noticias disponibles
        </div>
        <div style="color:#475569;font-size:14px;">
            El pipeline aún no ha corrido hoy o no encontró noticias recientes.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── SIDEBAR — FILTROS ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Filtros")
    st.markdown("---")

    # Filtro categoría
    st.markdown('<div class="filter-label">Categoría</div>', unsafe_allow_html=True)
    categorias_disponibles = sorted(set(n.get("categoria", "General") for n in noticias))
    cats_sel = st.multiselect(
        "Categorías",
        options=categorias_disponibles,
        default=categorias_disponibles,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Filtro relevancia
    st.markdown('<div class="filter-label">Relevancia</div>', unsafe_allow_html=True)
    solo_alta = st.checkbox("Solo alta relevancia", value=False)

    st.markdown("---")

    # Filtro fecha
    st.markdown('<div class="filter-label">Fecha</div>', unsafe_allow_html=True)
    fechas_disponibles = sorted(
        set(n.get("fecha") for n in noticias if n.get("fecha")),
        reverse=True
    )
    if fechas_disponibles:
        fechas_sel = st.multiselect(
            "Fechas",
            options=fechas_disponibles,
            default=fechas_disponibles,
            label_visibility="collapsed"
        )
    else:
        fechas_sel = []

    st.markdown("---")

    # Filtro fuente
    st.markdown('<div class="filter-label">Fuente</div>', unsafe_allow_html=True)
    fuentes_disponibles = sorted(set(n.get("fuente", "") for n in noticias if n.get("fuente")))
    fuentes_sel = st.multiselect(
        "Fuentes",
        options=fuentes_disponibles,
        default=fuentes_disponibles,
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown(f"<div style='font-size:11px;color:#334155;'>Pipeline: {fecha_act}</div>", unsafe_allow_html=True)


# ── FILTRADO ───────────────────────────────────────────────────────────────────

filtradas = noticias

if cats_sel:
    filtradas = [n for n in filtradas if n.get("categoria") in cats_sel]

if solo_alta:
    filtradas = [n for n in filtradas if n.get("relevancia") == "alta"]

if fechas_sel:
    filtradas = [n for n in filtradas if n.get("fecha") in fechas_sel or not n.get("fecha")]

if fuentes_sel:
    filtradas = [n for n in filtradas if n.get("fuente") in fuentes_sel]


# ── STATS BAR ─────────────────────────────────────────────────────────────────

stats_html = '<div class="stats-bar">'
for cat, color in CATEGORY_COLORS.items():
    count = sum(1 for n in filtradas if n.get("categoria") == cat)
    if count:
        stats_html += f'''
        <div class="stat-item">
            <span class="stat-num" style="color:{color};">{count}</span>
            <span class="stat-label">{cat}</span>
        </div>'''
stats_html += "</div>"
st.markdown(stats_html, unsafe_allow_html=True)


# ── GRID DE CARDS ──────────────────────────────────────────────────────────────

if not filtradas:
    st.info("No hay noticias con los filtros seleccionados.")
else:
    # 2 columnas
    col1, col2 = st.columns(2)
    for i, n in enumerate(filtradas):
        with (col1 if i % 2 == 0 else col2):
            render_card(n)
