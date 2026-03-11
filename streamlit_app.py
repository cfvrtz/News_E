"""
streamlit_app.py — Dashboard de noticias del sector eléctrico chileno.
"""

import streamlit as st
import requests
from datetime import datetime

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────────

GITHUB_USER = "cfvrtz"
GITHUB_REPO = "News_E"
GITHUB_API_RELEASES = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

CATEGORY_COLORS = {
    "Transmisión":         "#f5c518",
    "Generación & BESS":   "#4ade80",
    "Regulación":          "#60a5fa",
    "Mercado & Contratos": "#c084fc",
    "Combustibles & Gas":  "#f97316",
    "Institucional":       "#fb7185",
}

CATEGORY_ICONS = {
    "Transmisión":         "🔌",
    "Generación & BESS":   "⚡",
    "Regulación":          "📋",
    "Mercado & Contratos": "📊",
    "Combustibles & Gas":  "🛢️",
    "Institucional":       "🏛️",
}

# ── PÁGINA ─────────────────────────────────────────────────────────────────────

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
    font-size: 36px;
    font-weight: 900;
    color: #f1f5f9;
    line-height: 1.1;
    margin: 0 0 6px;
}
.header-accent { color: #f5c518; }
.header-sub { color: #64748b; font-size: 14px; margin: 0 0 24px; }

/* Pills de filtro rápido */
.pills-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
}
.pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid;
    transition: all 0.15s;
}

/* Stats bar */
.stats-bar {
    background: #0d1528;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 20px;
    display: flex;
    gap: 28px;
    flex-wrap: wrap;
    align-items: center;
}
.stat-item { display: flex; gap: 6px; align-items: baseline; }
.stat-num { font-family: 'Playfair Display', serif; font-size: 22px; font-weight: 700; }
.stat-label { font-size: 11px; color: #475569; }

/* Cards */
.news-card {
    background: #0d1528;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}
.news-card:hover {
    border-color: rgba(245,197,24,0.15);
    box-shadow: 0 6px 24px rgba(0,0,0,0.25);
}
.card-top-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.card-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    margin-top: 8px;
}
.cat-badge {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    border-radius: 6px;
    padding: 3px 9px;
}
.rel-alta {
    font-size: 10px; font-weight: 700;
    color: #f5c518;
    background: rgba(245,197,24,0.08);
    border: 1px solid rgba(245,197,24,0.25);
    border-radius: 6px; padding: 3px 9px;
}
.rel-media {
    font-size: 10px; font-weight: 600;
    color: #475569;
    border-radius: 6px; padding: 3px 9px;
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
    line-height: 1.65;
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
.card-link {
    display: inline-block;
    color: #60a5fa;
    font-size: 12px;
    text-decoration: none;
    margin-bottom: 12px;
}

/* Sidebar */
section[data-testid="stSidebar"] { background: #0d1528 !important; border-right: 1px solid rgba(245,197,24,0.08); }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ── CARGA DE DATOS ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_noticias():
    try:
        r = requests.get(GITHUB_API_RELEASES, timeout=15)
        r.raise_for_status()
        release = r.json()
        asset_url = next(
            (a["browser_download_url"] for a in release.get("assets", [])
             if a["name"] == "noticias.json"),
            None
        )
        if not asset_url:
            return {"error": "No se encontró noticias.json en el último release", "noticias": []}
        r2 = requests.get(asset_url, timeout=15)
        r2.raise_for_status()
        return r2.json()
    except Exception as e:
        return {"error": str(e), "noticias": [], "fecha_actualizacion": None}


def render_card(n):
    cat = n.get("categoria", "General")
    color = CATEGORY_COLORS.get(cat, "#94a3b8")
    rel = n.get("relevancia", "media")
    fuente = n.get("fuente") or "—"
    fecha = n.get("fecha") or "—"
    titulo = n.get("titulo") or ""
    resumen = n.get("resumen") or ""
    url = n.get("url") or ""

    rel_html = (
        '<span class="rel-alta">★ Alta</span>'
        if rel == "alta"
        else '<span class="rel-media">Media</span>'
    )

    link_html = (
        f'<a class="card-link" href="{url}" target="_blank">🔗 Ver fuente →</a><br>'
        if url else ""
    )

    # Color hex sin # para uso en clases inline
    c = color

    html = f"""<div class="news-card">
  <div class="card-top-bar" style="background:{c};"></div>
  <div class="card-meta">
    <span class="cat-badge" style="color:{c};background:{c}22;border:1px solid {c}44;">{cat}</span>
    {rel_html}
  </div>
  <div class="card-title">{titulo}</div>
  <div class="card-summary">{resumen}</div>
  {link_html}
  <div class="card-footer">
    <span>{fuente}</span>
    <span>{fecha}</span>
  </div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="header-badge">⚡ Monitor Energético</div>
<div class="header-title">Sector Eléctrico <span class="header-accent">Chile</span></div>
<div class="header-sub">Transmisión · Generación · Regulación · Mercado</div>
""", unsafe_allow_html=True)

# Botón actualizar
if st.button("⟳ Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

# ── CARGA ──────────────────────────────────────────────────────────────────────

data = cargar_noticias()

if "error" in data and data["error"]:
    st.error(f"No se pudo cargar el JSON: {data['error']}")
    st.stop()

noticias     = data.get("noticias", [])
fecha_act    = data.get("fecha_actualizacion", "—")
total_rev    = data.get("total_revisadas", "—")
estado       = data.get("estado", "ok")

if estado == "fallback":
    st.warning(f"Claude no pudo procesar: {data.get('motivo', '')} — mostrando titulares sin resumir.")

if not noticias:
    st.info("Sin noticias disponibles. El pipeline aún no ha corrido hoy.")
    st.stop()

# ── SIDEBAR ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Filtros")
    st.caption(f"Actualizado: {fecha_act}")
    st.divider()

    solo_alta = st.toggle("⭐ Solo alta relevancia", value=False)
    st.divider()

    st.markdown("**Categoría**")
    categorias_disponibles = sorted(set(n.get("categoria", "General") for n in noticias))
    cats_sel = st.multiselect(
        "cat", options=categorias_disponibles, default=categorias_disponibles,
        label_visibility="collapsed"
    )
    st.divider()

    st.markdown("**Fecha**")
    fechas_disponibles = sorted(
        set(n.get("fecha") for n in noticias if n.get("fecha")), reverse=True
    )
    if fechas_disponibles:
        fechas_sel = st.multiselect(
            "fecha", options=fechas_disponibles, default=fechas_disponibles,
            label_visibility="collapsed"
        )
    else:
        fechas_sel = []
    st.divider()

    st.markdown("**Fuente**")
    fuentes_disponibles = sorted(set(n.get("fuente", "") for n in noticias if n.get("fuente")))
    fuentes_sel = st.multiselect(
        "fuente", options=fuentes_disponibles, default=fuentes_disponibles,
        label_visibility="collapsed"
    )

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

# ── PILLS FILTRO RÁPIDO POR CATEGORÍA ─────────────────────────────────────────

st.markdown("**Filtro rápido por categoría:**")
cat_filter = st.radio(
    "cat_quick",
    options=["Todas"] + categorias_disponibles,
    horizontal=True,
    label_visibility="collapsed"
)
if cat_filter != "Todas":
    filtradas = [n for n in filtradas if n.get("categoria") == cat_filter]

# ── STATS BAR ─────────────────────────────────────────────────────────────────

stats_html = '<div class="stats-bar">'
stats_html += f'<div class="stat-item"><span class="stat-num" style="color:#f1f5f9;">{len(filtradas)}</span><span class="stat-label">total</span></div>'
for cat, color in CATEGORY_COLORS.items():
    count = sum(1 for n in filtradas if n.get("categoria") == cat)
    if count:
        icon = CATEGORY_ICONS.get(cat, "•")
        stats_html += f'<div class="stat-item"><span class="stat-num" style="color:{color};">{count}</span><span class="stat-label">{icon} {cat}</span></div>'
stats_html += f'<div style="margin-left:auto;font-size:11px;color:#334155;">{total_rev} revisadas · {fecha_act}</div>'
stats_html += '</div>'
st.markdown(stats_html, unsafe_allow_html=True)

# ── GRID ───────────────────────────────────────────────────────────────────────

if not filtradas:
    st.info("No hay noticias con los filtros seleccionados.")
else:
    col1, col2 = st.columns(2)
    for i, n in enumerate(filtradas):
        with (col1 if i % 2 == 0 else col2):
            render_card(n)
