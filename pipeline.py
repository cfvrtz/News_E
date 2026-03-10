"""
pipeline.py — Orquesta scraper → summarizer → guarda JSON en GitHub Releases.
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


def subir_a_releases(data: dict, gh_token: str, repo: str):
    """Sube el JSON como asset en GitHub Releases (tag: 'latest-news')."""
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    tag = "latest-news"
    api = f"https://api.github.com/repos/{repo}"

    # Borrar release anterior si existe
    r = requests.get(f"{api}/releases/tags/{tag}", headers=headers)
    if r.status_code == 200:
        release_id = r.json()["id"]
        requests.delete(f"{api}/releases/{release_id}", headers=headers)
        log.info("Release anterior eliminado")

    # Borrar tag anterior si existe
    requests.delete(f"{api}/git/refs/tags/{tag}", headers=headers)

    # Crear nuevo release
    payload = {
        "tag_name": tag,
        "name": f"Noticias {datetime.now().strftime('%d/%m/%Y')}",
        "body": f"Actualizado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "draft": False,
        "prerelease": False
    }
    r = requests.post(f"{api}/releases", headers=headers, json=payload)
    r.raise_for_status()
    release = r.json()
    upload_url = release["upload_url"].replace("{?name,label}", "")

    # Subir JSON
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    headers_upload = {**headers, "Content-Type": "application/json"}
    r = requests.post(
        f"{upload_url}?name=noticias.json",
        headers=headers_upload,
        data=json_bytes
    )
    r.raise_for_status()
    log.info(f"✅ JSON subido: {r.json()['browser_download_url']}")
    return r.json()["browser_download_url"]


def run():
    # Leer variables de entorno
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    gh_token = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")  # formato: "usuario/repo"

    if not api_key:
        raise ValueError("Falta ANTHROPIC_API_KEY")
    if not gh_token:
        raise ValueError("Falta GH_TOKEN")
    if not repo:
        raise ValueError("Falta GITHUB_REPOSITORY")

    client = anthropic.Anthropic(api_key=api_key)

    # 1. Scraping
    log.info("=== PASO 1: Scraping ===")
    noticias_raw = scrape_all(dias_atras=2)

    if not noticias_raw:
        log.warning("No se encontraron noticias. Abortando.")
        return

    # 2. Summarizar con Claude
    log.info("=== PASO 2: Procesando con Claude ===")
    resultado = summarize(noticias_raw, client)

    # 3. Subir a GitHub Releases
    log.info("=== PASO 3: Subiendo a GitHub Releases ===")
    url = subir_a_releases(resultado, gh_token, repo)
    log.info(f"Pipeline completado. URL: {url}")


if __name__ == "__main__":
    run()
