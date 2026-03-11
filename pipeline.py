"""
pipeline_resiliente.py — Orquesta scraper → summarizer → guarda JSON en GitHub Releases.
Versión tolerante a fallos: si una fuente o paso falla, el pipeline sigue.
"""

import os
import json
import logging
import requests
from datetime import datetime
import anthropic

from scraper import scrape_all
from summarizer import summarize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def _safe_request(method, url, **kwargs):
    try:
        return requests.request(method, url, timeout=30, **kwargs)
    except Exception as e:
        log.warning(f"Fallo request {method} {url}: {e}")
        return None


def _resultado_vacio(motivo: str) -> dict:
    ahora = datetime.now().strftime('%d/%m/%Y %H:%M')
    return {
        "fecha_actualizacion": ahora,
        "total_revisadas": 0,
        "noticias": [],
        "estado": "sin_resultados",
        "motivo": motivo,
    }


def subir_a_releases(data: dict, gh_token: str, repo: str):
    """Sube el JSON como asset en GitHub Releases (tag: 'latest-news')."""
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    tag = "latest-news"
    api = f"https://api.github.com/repos/{repo}"

    # Borrar release anterior si existe
    r = _safe_request("GET", f"{api}/releases/tags/{tag}", headers=headers)
    if r is not None and r.status_code == 200:
        release_id = r.json().get("id")
        if release_id:
            r_del = _safe_request("DELETE", f"{api}/releases/{release_id}", headers=headers)
            if r_del is not None and r_del.status_code in (204, 200):
                log.info("Release anterior eliminado")
            else:
                log.warning("No se pudo eliminar release anterior; se intentará seguir igual")

    # Borrar tag anterior si existe
    r_tag = _safe_request("DELETE", f"{api}/git/refs/tags/{tag}", headers=headers)
    if r_tag is not None and r_tag.status_code not in (204, 200, 404):
        log.warning(f"No se pudo borrar tag anterior: {r_tag.status_code} {r_tag.text[:200]}")

    # Crear nuevo release
    payload = {
        "tag_name": tag,
        "name": f"Noticias {datetime.now().strftime('%d/%m/%Y')}",
        "body": f"Actualizado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "draft": False,
        "prerelease": False
    }
    r = _safe_request("POST", f"{api}/releases", headers=headers, json=payload)
    if r is None:
        raise RuntimeError("No se pudo conectar a GitHub para crear el release")
    if not r.ok:
        raise RuntimeError(f"Error creando release: {r.status_code} {r.text[:300]}")

    release = r.json()
    upload_url = release["upload_url"].replace("{?name,label}", "")

    # Subir JSON
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    headers_upload = {**headers, "Content-Type": "application/json"}
    r = _safe_request(
        "POST",
        f"{upload_url}?name=noticias.json",
        headers=headers_upload,
        data=json_bytes
    )
    if r is None:
        raise RuntimeError("No se pudo conectar a GitHub para subir el JSON")
    if not r.ok:
        raise RuntimeError(f"Error subiendo JSON: {r.status_code} {r.text[:300]}")

    log.info(f"✅ JSON subido: {r.json()['browser_download_url']}")
    return r.json()["browser_download_url"]


def run():
    # Leer variables de entorno
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")  # formato: "usuario/repo"

    if not gh_token:
        raise ValueError("Falta GITHUB_TOKEN o GH_TOKEN")
    
    if not repo:
        raise ValueError("Falta GITHUB_REPOSITORY")

    client = anthropic.Anthropic(api_key=api_key) if api_key else None
    if not api_key:
        log.warning("No hay ANTHROPIC_API_KEY. Se omitirá el resumen con Claude y se subirá resultado base.")

    # 1. Scraping
    log.info("=== PASO 1: Scraping ===")
    try:
        noticias_raw = scrape_all(dias_atras=2)
    except Exception as e:
        log.exception(f"Fallo general en scraping: {e}")
        noticias_raw = []

    # 2. Construcción del resultado
    if noticias_raw:
        if client is not None:
            log.info("=== PASO 2: Procesando con Claude ===")
            try:
                resultado = summarize(noticias_raw, client)
            except Exception as e:
                log.exception(f"Fallo en summarize: {e}")
                resultado = {
                    "fecha_actualizacion": datetime.now().strftime('%d/%m/%Y %H:%M'),
                    "total_revisadas": len(noticias_raw),
                    "noticias": noticias_raw,
                    "estado": "fallback_scraper",
                    "motivo": f"No se pudo resumir con Claude: {type(e).__name__}",
                }
        else:
            resultado = {
                "fecha_actualizacion": datetime.now().strftime('%d/%m/%Y %H:%M'),
                "total_revisadas": len(noticias_raw),
                "noticias": noticias_raw,
                "estado": "sin_claude",
                "motivo": "No se configuró ANTHROPIC_API_KEY",
            }
    else:
        log.warning("No se encontraron noticias. Se subirá JSON vacío para no cortar el pipeline.")
        resultado = _resultado_vacio("No se pudo acceder a suficientes fuentes o no hubo resultados recientes")

    # 3. Subir a GitHub Releases
    log.info("=== PASO 3: Subiendo a GitHub Releases ===")
    url = subir_a_releases(resultado, gh_token, repo)
    log.info(f"Pipeline completado. URL: {url}")


if __name__ == "__main__":
    run()
