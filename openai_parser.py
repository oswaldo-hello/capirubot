import os
import re
import json
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORY_DEFINITIONS = [
    ("INGRESO", "Ingresos", "Todo tipo de ingresos"),
    ("INVERSIONES", "Inversiones", "Dinero invertido"),
    ("GASTO", "BASICO", "Gastos básicos no incluidos en otras categorías. Incluye pagos de servicios, ropa, zapatos, zapatillas, etc."),
    ("GASTO", "COMIDA", "Comida y restaurantes"),
    ("GASTO", "COSAS", "Compras personales"),
    ("GASTO", "ENTRETENIMIENTO", "Streaming, cine, etc."),
    ("GASTO", "ESTUDIOS", "Educación"),
    ("GASTO", "OTROS", "Gastos imprevistos"),
    ("GASTO", "VIAJES", "Viajes y hoteles"),
    ("GASTO", "SALUD", "Salud y medicinas"),
    ("GASTO", "TRANSPORTE", "Taxis, buses, etc."),
]

lima_tz = pytz.timezone("America/Lima")

def parse_relative_date(user_text):
    now = datetime.now(lima_tz).date()
    text_lower = user_text.lower()

    if "hoy" in text_lower:
        return now.isoformat()
    elif "ayer" in text_lower:
        return (now - timedelta(days=1)).isoformat()
    elif "antes de ayer" in text_lower:
        return (now - timedelta(days=2)).isoformat()

    match = re.search(r"(\d{1,2})[/-](\d{1,2})", user_text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        try:
            return datetime(now.year, month, day).date().isoformat()
        except ValueError:
            return now.isoformat()

    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    for mes, num_mes in meses.items():
        match = re.search(rf"(\d{{1,2}})\s+de\s+{mes}", user_text, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            try:
                return datetime(now.year, num_mes, day).date().isoformat()
            except ValueError:
                return now.isoformat()

    return now.isoformat()

def parse_with_openai(user_text):

    fecha_actual = datetime.now(lima_tz).strftime("%Y-%m-%d")
    
    category_text = "\n".join([f"- {c} | {sub} → {desc}" for c, sub, desc in CATEGORY_DEFINITIONS])

    system_prompt = f"""
Eres un asistente que extrae movimientos financieros en formato JSON.

La fecha actual es {fecha_actual} en zona horaria America/Lima.
Interpreta cualquier referencia de fecha relativa a hoy.

Salida esperada:
{{
  "date": "YYYY-MM-DD",
  "amount": 123.45,
  "currency": "PEN",
  "category": "INGRESO|INVERSIONES|GASTO",
  "subcategory": "BASICO|COMIDA|COSAS|ENTRETENIMIENTO|ESTUDIOS|OTROS|VIAJES|SALUD|TRANSPORTE",
  "description": "texto original"
}}

Definiciones de categorías:
{category_text}

Reglas:
1) Usa las definiciones para clasificar.
2) La categoría y subcategoría deben ir en campos separados.
3) Devuelve SOLO JSON, sin texto adicional.
"""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0
    )

    try:
        content = completion.choices[0].message.content
        parsed = json.loads(content)
    except (AttributeError, KeyError, IndexError) as e:
        print(f"[ERROR] Estructura inesperada en respuesta OpenAI: {e}")
        return None
    except json.JSONDecodeError:
        print("[ERROR] No se pudo decodificar la respuesta como JSON")
        return None

    # Validar y ajustar fecha
    if not parsed.get("date") or not re.match(r"\d{4}-\d{2}-\d{2}", parsed["date"]):
        parsed["date"] = parse_relative_date(user_text)

    # Ajustar moneda
    if "sol" in parsed.get("currency", "").lower():
        parsed["currency"] = "PEN"

    # Validar categoría y subcategoría
    if "category" in parsed and "|" in parsed["category"]:
        cat_parts = [p.strip() for p in parsed["category"].split("|", 1)]
        parsed["category"] = cat_parts[0]
        if len(cat_parts) > 1 and not parsed.get("subcategory"):
            parsed["subcategory"] = cat_parts[1]

    return parsed
