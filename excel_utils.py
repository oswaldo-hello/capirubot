import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# Configuración de zona horaria
lima_tz = pytz.timezone("America/Lima")

# Ruta al archivo JSON de credenciales (ajusta con tu nombre real del archivo)
GOOGLE_CREDENTIALS_FILE = "capirubot-af8f308ba262.json"

# ID del Google Sheet (lo obtienes de la URL del documento)
# Ejemplo de URL:
# https://docs.google.com/spreadsheets/d/1ABC123xyz4567890abcdef/edit#gid=0
# El ID es lo que va después de "/d/" y antes de "/edit"
GOOGLE_SHEET_ID = "1hCyGQT8eOKOZKfiFna83oSHAR1YVt9Bk996RapDUrT0"

# Alcances de la API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Autenticación
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# Abrir el Google Sheet
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1  # usa la primera hoja

def append_transaction(date, category, subcategory, amount, comentario, fecha_registro):
    """Agrega una fila al Google Sheet."""
    sheet.append_row([date, category, subcategory, amount, comentario, fecha_registro], value_input_option="USER_ENTERED")

def read_transactions():
    """Lee el Google Sheet y devuelve lista de diccionarios."""
    data = sheet.get_all_values()
    if len(data) < 2:
        return []
    headers = data[0]
    rows = data[1:]
    return [
        dict(zip(headers, row))
        for row in rows
    ]
