"""
summarizer_resiliente.py — Versión tolerante a fallos.
Si Claude falla o responde JSON inválido, devuelve fallback con noticias crudas.
"""

import anthropic
import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)

CATEGORIAS = [
    "Transmisión",
    "Generación & BESS",
    "Regulación",
    "Mercado & Contratos",
    "Combustibles & Gas",
    "Institucional",
]

SYSTEM_PROMPT = """Eres un analista especializado en el sector eléctrico chileno.
Recibirás una lista de titulares de noticias con su fuente, fecha y URL.
Tu tarea es:
1. Seleccionar las más relevantes según el criterio editorial definido
2. Descartar duplicados o noticias irrelevantes
3. Escribir un resumen técnico de 2-3 oraciones por cada noticia seleccionada
4. Asignar categoría y relevancia

Devuelve ÚNICAMENTE un JSON válido."""


def _fallback(noticias_raw: list, motivo: str) -> dict:
    return {
        "fecha_actualizacion": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "total_revisadas": len(noticias_raw),
        "noticias": noticias_raw,
        "estado": "fallback",
        "motivo": motivo,
    }


def summarize(noticias_raw: list, client: anthropic.Anthropic) -> dict:
    if not noticias_raw:
        log.warning("No hay noticias para procesar")
        return _fallback([], "No hay noticias para procesar")

    lines = []
    for i, n in enumerate(noticias_raw, 1):
        fecha = n.get("fecha") or "fecha desconocida"
        fuente = n.get("fuente") or "fuente desconocida"
        url = n.get("url") or "sin URL"
        titulo = n.get("titulo", "(sin título)")
        lines.append(f"{i}. [{fuente} | {fecha}] {titulo}\n   URL: {url}")

    input_text = "\n\n".join(lines)
    total = len(noticias_raw)

    log.info(f"Enviando {total} titulares a Claude para procesar...")

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Procesa estos {total} titulares del sector eléctrico chileno y devuelve el JSON estructurado:\n\n{input_text}"
                }
            ]
        )
        raw = message.content[0].text
    except Exception as e:
        log.exception(f"Claude falló: {e}")
        return _fallback(noticias_raw, f"Claude falló: {type(e).__name__}")

    parsed = None
    try:
        parsed = json.loads(raw.strip())
    except Exception:
        pass

    if not parsed:
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                pass

    if not parsed:
        log.error("Claude no devolvió JSON válido")
        return _fallback(noticias_raw, "Claude no devolvió JSON válido")

    parsed["total_revisadas"] = total
    if "fecha_actualizacion" not in parsed:
        parsed["fecha_actualizacion"] = datetime.now().strftime('%d/%m/%Y %H:%M')
    if "noticias" not in parsed or not isinstance(parsed["noticias"], list):
        parsed["noticias"] = noticias_raw
        parsed["estado"] = "fallback_parcial"
        parsed["motivo"] = "Claude devolvió estructura incompleta"

    log.info(f"Claude seleccionó {len(parsed.get('noticias', []))} noticias de {total}")
    return parsed
