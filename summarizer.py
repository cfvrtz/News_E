"""
summarizer.py — Llama a Claude API para categorizar, resumir y asignar
relevancia a las noticias extraídas por scraper.py.
"""

import anthropic
import json
import logging

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

CRITERIO EDITORIAL — INCLUIR:
✅ Transmisión: líneas, subestaciones, desconexiones, expansión, auditorías
✅ Generación & BESS: proyectos solar/eólico/hidro/baterías, RCA, financiamiento, operaciones
✅ Regulación: decretos, leyes, normas técnicas, CNE, SEC, Diario Oficial, procedimientos
✅ Mercado & Contratos: tarifas, licitaciones, precios spot, compensaciones, reliquidaciones
✅ Combustibles & Gas: petróleo, GNL, gas natural, impacto internacional en Chile
✅ Institucional: multas, conflictos regulatorios, fiscalización, apagones, decisiones sistémicas

EXCLUIR:
❌ Eventos, seminarios o webinars sin contenido técnico nuevo
❌ Nombramientos ejecutivos menores sin impacto sistémico
❌ Noticias internacionales sin vínculo directo con Chile
❌ Duplicados (quédate con la fuente más técnica/completa)

EJEMPLOS DE ALTA RELEVANCIA:
- Desconexiones o rechazos en líneas clave (500kV, líneas críticas)
- Estadísticas oficiales con cifras (MW, MWh, USD, GWh)
- Financiamientos cerrados de proyectos grandes
- Aprobaciones ambientales (RCA) con capacidad concreta
- Conflictos institucionales Coordinador/SEC/Contraloría
- Publicaciones del Diario Oficial con impacto en el sector
- Modificaciones de normas técnicas (NTCO, PMGD, etc.)
- Nuevas licitaciones o resultados de licitaciones de suministro

Devuelve ÚNICAMENTE un JSON válido con esta estructura, sin texto adicional:
{
  "fecha_actualizacion": "DD/MM/YYYY HH:MM",
  "total_revisadas": <número de titulares recibidos>,
  "noticias": [
    {
      "titulo": "Título limpio y directo",
      "resumen": "Resumen técnico en 2-3 oraciones con cifras concretas si las hay",
      "categoria": "una de: Transmisión | Generación & BESS | Regulación | Mercado & Contratos | Combustibles & Gas | Institucional",
      "fuente": "nombre del medio o institución",
      "fecha": "DD/MM/YYYY o null",
      "relevancia": "alta | media",
      "url": "URL directa o null"
    }
  ]
}"""


def summarize(noticias_raw: list, client: anthropic.Anthropic) -> dict:
    """
    Recibe lista de noticias del scraper y devuelve JSON procesado por Claude.
    """
    if not noticias_raw:
        log.warning("No hay noticias para procesar")
        return {"noticias": [], "total_revisadas": 0}

    # Formatear input para Claude
    lines = []
    for i, n in enumerate(noticias_raw, 1):
        fecha = n.get("fecha") or "fecha desconocida"
        fuente = n.get("fuente") or "fuente desconocida"
        url = n.get("url") or "sin URL"
        lines.append(f"{i}. [{fuente} | {fecha}] {n['titulo']}\n   URL: {url}")

    input_text = "\n\n".join(lines)
    total = len(noticias_raw)

    log.info(f"Enviando {total} titulares a Claude para procesar...")

    message = client.messages.create(
        model="claude-sonnet-4-5-20251001",  # Haiku es suficiente y más barato para esto
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Procesa estos {total} titulares del sector eléctrico chileno "
                           f"y devuelve el JSON estructurado:\n\n{input_text}"
            }
        ]
    )

    raw = message.content[0].text

    # Parsear JSON robusto
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
        log.error(f"Respuesta: {raw[:300]}")
        return {"noticias": [], "total_revisadas": total, "error": raw[:200]}

    parsed["total_revisadas"] = total
    log.info(f"Claude seleccionó {len(parsed.get('noticias', []))} noticias de {total}")
    return parsed
