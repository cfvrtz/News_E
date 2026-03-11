"""
summarizer.py — Llama a Claude API para filtrar, categorizar y resumir
las noticias extraídas por scraper.py.
"""

import anthropic
import json
import logging
import re
from datetime import datetime

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un analista especializado en el sector eléctrico chileno con criterio editorial estricto.

Recibirás una lista numerada de titulares con fuente, fecha y URL.
Tu tarea es:
1. DESCARTAR las noticias irrelevantes (ver criterio abajo)
2. Para las relevantes: escribir resumen técnico de 2-3 oraciones con cifras concretas
3. Asignar categoría y relevancia

═══════════════════════════════════════
INCLUIR — alta prioridad:
═══════════════════════════════════════
✅ Transmisión: líneas, subestaciones, desconexiones, auditorías, expansión (ej: línea 500kV, Decreto 7T)
✅ Generación & BESS: proyectos solar/eólico/hidro/baterías con MW, MWh, USD concretos; RCA; financiamiento; inicio operaciones
✅ Regulación: decretos, leyes, normas técnicas (NTCO, PMGD), resoluciones CNE/SEC, Diario Oficial
✅ Mercado & Contratos: tarifas, licitaciones, precios spot, compensaciones, reliquidaciones, VAD
✅ Combustibles & Gas: petróleo, GNL, gas natural argentino, impacto en precios locales chilenos
✅ Institucional: multas SEC, conflictos Coordinador/SEC/Contraloría, apagones y consecuencias

EJEMPLOS DE ALTA RELEVANCIA:
- "Coordinador rechazó solicitud de desconexión en línea 500kV Nueva Pan de Azúcar-Polpaico"
- "CNE contabiliza 73 proyectos BESS en construcción con 7.253 MW"
- "SEA aprueba proyecto solar con BESS de US$130M en región del Maule"
- "CEN denunció a la SEC ante Contraloría"
- "Coordinador ajusta metodología para auditoría técnica Decreto 7T"
- "El petróleo a US$100 pone presión a economía local: hasta 1 punto de inflación"
- "Coordinador inicia proceso para actualizar proyecciones de demanda hasta 2046"

═══════════════════════════════════════
DESCARTAR siempre:
═══════════════════════════════════════
❌ Noticias sin relación con el sector eléctrico/energético chileno
❌ Economía general, política, salud, minería no energética
❌ Noticias internacionales sin impacto directo en precios/suministro en Chile
❌ Nombramientos ejecutivos menores (excepto director Coordinador o CNE)
❌ Eventos, seminarios, webinars sin contenido técnico nuevo
❌ Opinión o columnas sin información nueva concreta
❌ Duplicados (quédate con la versión más completa/técnica)

EJEMPLOS A DESCARTAR:
- "Chile avanza un puesto en ranking global de libertad económica"
- "Suseso proyecta nuevo desplome de licencias médicas en 2026"
- "La otra herencia de Boric: más de 5.000 juicios"
- "Subrei cierra gestión con tercera oferta comercial de India"
- "Grupo CAP disminuyó sus pérdidas en 80%"
- "Día de la Mujer: alumna de liceo técnico-profesional"
- "Se gradúan participantes del Programa +Mujeres del Servicio Civil"

═══════════════════════════════════════
FORMATO DE RESPUESTA
═══════════════════════════════════════
Devuelve ÚNICAMENTE este JSON válido, sin texto adicional, sin markdown, sin explicaciones:
{
  "fecha_actualizacion": "DD/MM/YYYY HH:MM",
  "total_revisadas": <número entero>,
  "noticias": [
    {
      "titulo": "Título limpio y directo",
      "resumen": "Resumen técnico 2-3 oraciones con cifras concretas si las hay",
      "categoria": "Transmisión | Generación & BESS | Regulación | Mercado & Contratos | Combustibles & Gas | Institucional",
      "fuente": "nombre del medio",
      "fecha": "DD/MM/YYYY o null",
      "relevancia": "alta | media",
      "url": "URL o null"
    }
  ]
}

IMPORTANTE: Responde SOLO con el JSON. Sin texto antes ni después."""


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
    ahora = datetime.now().strftime('%d/%m/%Y %H:%M')

    log.info(f"Enviando {total} titulares a Claude para procesar...")

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Hoy es {ahora}. Procesa estos {total} titulares, "
                        f"descarta los irrelevantes y devuelve SOLO el JSON:\n\n{input_text}"
                    )
                }
            ]
        )
        raw = message.content[0].text.strip()
        log.info(f"Respuesta Claude (primeros 300 chars): {raw[:300]}")
    except Exception as e:
        log.exception(f"Claude falló: {e}")
        return _fallback(noticias_raw, f"Claude falló: {type(e).__name__}")

    # Parseo robusto — 3 intentos
    parsed = None

    try:
        parsed = json.loads(raw)
    except Exception:
        pass

    if not parsed:
        m = re.search(r"```json\s*([\s\S]*?)```", raw)
        if m:
            try:
                parsed = json.loads(m.group(1).strip())
            except Exception:
                pass

    if not parsed:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                pass

    if not parsed:
        log.error(f"Claude no devolvió JSON válido. Respuesta: {raw[:400]}")
        return _fallback(noticias_raw, f"JSON inválido. Respuesta: {raw[:200]}")

    parsed.setdefault("fecha_actualizacion", ahora)
    parsed["total_revisadas"] = total

    if "noticias" not in parsed or not isinstance(parsed.get("noticias"), list):
        log.error("JSON sin campo 'noticias'")
        return _fallback(noticias_raw, "JSON sin campo noticias")

    log.info(f"✅ Claude seleccionó {len(parsed['noticias'])} noticias de {total}")
    return parsed
