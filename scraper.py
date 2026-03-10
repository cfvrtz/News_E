"""
scraper.py — Extrae titulares, fechas, fuentes y URLs de fuentes de noticias
del sector eléctrico chileno.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 15


def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        log.warning(f"No se pudo acceder a {url}: {e}")
        return None


def parse_fecha_es(texto):
    """Convierte texto de fecha en español a DD/MM/YYYY."""
    if not texto:
        return None
    texto = texto.strip().lower()
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    # Formato: "Lunes, 10 de marzo de 2026" o "10 de marzo de 2026"
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto)
    if m:
        dia, mes_str, anio = m.group(1), m.group(2), m.group(3)
        mes = meses.get(mes_str)
        if mes:
            return f"{int(dia):02d}/{mes:02d}/{anio}"
    # Formato: "Mar 10, 2026" o "10-03-2026"
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", texto)
    if m:
        return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    return None


# ── FUENTES ────────────────────────────────────────────────────────────────────

def scrape_clipper():
    """CEN Clipper — resumen diario. Titulares con fuente y fecha debajo."""
    log.info("Scraping: CEN Clipper")
    url = "https://clipper.e-clip.cl/clipper/clip/cen"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    # Los titulares vienen como <h3> o <h2> con links
    for tag in soup.find_all(["h2", "h3"]):
        a = tag.find("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        link = a.get("href", "")
        if not link.startswith("http"):
            link = None

        # La fuente y fecha vienen en el elemento siguiente
        fuente, fecha = None, None
        siguiente = tag.find_next_sibling()
        if siguiente:
            texto = siguiente.get_text(strip=True)
            # Formato: "Diario Financiero - Jueves, 5 de Marzo de 2026"
            if " - " in texto:
                partes = texto.split(" - ", 1)
                fuente = partes[0].strip()
                fecha = parse_fecha_es(partes[1]) if len(partes) > 1 else None
            else:
                fecha = parse_fecha_es(texto)

        if titulo and len(titulo) > 15:
            noticias.append({
                "titulo": titulo,
                "fuente": fuente or "CEN Clipper",
                "fecha": fecha,
                "url": link,
                "origen": "CEN Clipper"
            })

    log.info(f"  → {len(noticias)} noticias encontradas")
    return noticias


def scrape_cne():
    """CNE Prensa — https://www.cne.cl/prensa/"""
    log.info("Scraping: CNE")
    url = "https://www.cne.cl/prensa/"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    for h3 in soup.find_all("h3"):
        a = h3.find("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        link = a.get("href", "")
        if link and not link.startswith("http"):
            link = "https://www.cne.cl" + link

        # Buscar fecha cercana
        fecha = None
        for sib in [h3.find_next_sibling(), h3.parent.find_next_sibling()]:
            if sib:
                t = sib.get_text(strip=True)
                fecha = parse_fecha_es(t)
                if fecha:
                    break

        if titulo and len(titulo) > 10:
            noticias.append({
                "titulo": titulo,
                "fuente": "CNE",
                "fecha": fecha,
                "url": link,
                "origen": "CNE"
            })

    log.info(f"  → {len(noticias)} noticias encontradas")
    return noticias


def scrape_coordinador():
    """Coordinador Eléctrico Nacional — https://www.coordinador.cl/novedades/"""
    log.info("Scraping: Coordinador Eléctrico")
    url = "https://www.coordinador.cl/novedades/"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    for h in soup.find_all(["h2", "h3", "h4"]):
        a = h.find("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        link = a.get("href", "")
        if link and not link.startswith("http"):
            link = "https://www.coordinador.cl" + link

        fecha = None
        parent = h.parent
        for el in parent.find_all(["span", "p", "time"]):
            t = el.get_text(strip=True)
            fecha = parse_fecha_es(t)
            if fecha:
                break

        if titulo and len(titulo) > 10:
            noticias.append({
                "titulo": titulo,
                "fuente": "Coordinador Eléctrico",
                "fecha": fecha,
                "url": link,
                "origen": "Coordinador Eléctrico"
            })

    log.info(f"  → {len(noticias)} noticias encontradas")
    return noticias


def scrape_sec():
    """SEC — https://www.sec.cl/categoria/noticias/"""
    log.info("Scraping: SEC")
    url = "https://www.sec.cl/categoria/noticias/"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    for h in soup.find_all(["h2", "h3"]):
        a = h.find("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        link = a.get("href", "")

        fecha = None
        parent = h.parent
        for el in parent.find_all(["span", "p", "time"]):
            t = el.get_text(strip=True)
            fecha = parse_fecha_es(t)
            if fecha:
                break

        if titulo and len(titulo) > 10:
            noticias.append({
                "titulo": titulo,
                "fuente": "SEC",
                "fecha": fecha,
                "url": link,
                "origen": "SEC"
            })

    log.info(f"  → {len(noticias)} noticias encontradas")
    return noticias


def scrape_ministerio():
    """Ministerio de Energía — https://energia.gob.cl/noticias"""
    log.info("Scraping: Ministerio de Energía")
    url = "https://energia.gob.cl/noticias"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    for h in soup.find_all(["h2", "h3"]):
        a = h.find("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        link = a.get("href", "")
        if link and not link.startswith("http"):
            link = "https://energia.gob.cl" + link

        fecha = None
        parent = h.parent
        for el in parent.find_all(["span", "p", "time", "div"]):
            t = el.get_text(strip=True)
            fecha = parse_fecha_es(t)
            if fecha:
                break

        if titulo and len(titulo) > 10:
            noticias.append({
                "titulo": titulo,
                "fuente": "Ministerio de Energía",
                "fecha": fecha,
                "url": link,
                "origen": "Ministerio de Energía"
            })

    log.info(f"  → {len(noticias)} noticias encontradas")
    return noticias


def scrape_electromineria():
    """Electrominería — https://electromineria.cl/category/panorama-energetico/"""
    log.info("Scraping: Electrominería")
    url = "https://electromineria.cl/category/panorama-energetico/"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    for h in soup.find_all(["h2", "h3"]):
        a = h.find("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        link = a.get("href", "")

        fecha = None
        parent = h.parent
        for el in parent.find_all(["span", "p", "time"]):
            t = el.get_text(strip=True)
            fecha = parse_fecha_es(t)
            if fecha:
                break

        if titulo and len(titulo) > 10:
            noticias.append({
                "titulo": titulo,
                "fuente": "Electrominería",
                "fecha": fecha,
                "url": link,
                "origen": "Electrominería"
            })

    log.info(f"  → {len(noticias)} noticias encontradas")
    return noticias


def scrape_diario_oficial():
    """Diario Oficial — edición del día."""
    log.info("Scraping: Diario Oficial")
    today = datetime.now().strftime("%d-%m-%Y")
    url = f"https://www.diariooficial.interior.gob.cl/edicionelectronica/select_edition.php?date={today}"
    soup = get_soup(url)
    if not soup:
        return []

    noticias = []
    # Buscar publicaciones del Ministerio de Energía, CNE, SEC
    keywords = ["energía", "eléctric", "cne", "sec", "potencia", "tarifa",
                "combustible", "generación", "transmisión", "distribución"]

    for a in soup.find_all("a"):
        titulo = a.get_text(strip=True)
        if len(titulo) < 15:
            continue
        titulo_lower = titulo.lower()
        if any(kw in titulo_lower for kw in keywords):
            link = a.get("href", "")
            if link and not link.startswith("http"):
                link = "https://www.diariooficial.interior.gob.cl" + link
            noticias.append({
                "titulo": titulo,
                "fuente": "Diario Oficial",
                "fecha": datetime.now().strftime("%d/%m/%Y"),
                "url": link,
                "origen": "Diario Oficial"
            })

    log.info(f"  → {len(noticias)} publicaciones relevantes encontradas")
    return noticias


# ── DEDUPLICACIÓN ──────────────────────────────────────────────────────────────

def deduplicar(noticias):
    """Elimina títulos casi idénticos (mismo tema, distintas fuentes)."""
    vistos = []
    resultado = []
    for n in noticias:
        titulo_norm = re.sub(r"[^a-záéíóúñ\s]", "", n["titulo"].lower()).strip()
        palabras = set(titulo_norm.split())
        es_dup = False
        for v in vistos:
            comun = palabras & v
            if len(comun) >= 5:  # 5+ palabras en común = probable duplicado
                es_dup = True
                break
        if not es_dup:
            vistos.append(palabras)
            resultado.append(n)
    return resultado


# ── FILTRO POR FECHA ───────────────────────────────────────────────────────────

def filtrar_por_fecha(noticias, dias=2):
    """Retiene noticias de los últimos N días. Las sin fecha igual pasan."""
    hoy = datetime.now()
    resultado = []
    for n in noticias:
        if not n.get("fecha"):
            resultado.append(n)  # sin fecha: igual incluir, Claude decide
            continue
        try:
            d, m, a = n["fecha"].split("/")
            fecha_dt = datetime(int(a), int(m), int(d))
            if (hoy - fecha_dt).days <= dias:
                resultado.append(n)
        except Exception:
            resultado.append(n)
    return resultado


# ── ENTRY POINT ────────────────────────────────────────────────────────────────

def scrape_all(dias_atras=2):
    """Ejecuta todos los scrapers y devuelve lista deduplicada."""
    fuentes = [
        scrape_clipper,
        scrape_cne,
        scrape_coordinador,
        scrape_sec,
        scrape_ministerio,
        scrape_electromineria,
        scrape_diario_oficial,
    ]

    todas = []
    for fn in fuentes:
        try:
            todas.extend(fn())
        except Exception as e:
            log.error(f"Error en {fn.__name__}: {e}")

    log.info(f"Total bruto: {len(todas)} noticias")
    filtradas = filtrar_por_fecha(todas, dias=dias_atras)
    log.info(f"Tras filtro de fecha ({dias_atras} días): {len(filtradas)}")
    dedup = deduplicar(filtradas)
    log.info(f"Tras deduplicación: {len(dedup)}")
    return dedup


if __name__ == "__main__":
    import json
    noticias = scrape_all()
    print(json.dumps(noticias, ensure_ascii=False, indent=2))
