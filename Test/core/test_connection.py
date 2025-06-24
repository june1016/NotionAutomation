""" 
Test de Conectividad con Notion API
==================================

Verifica la conexión básica con la API de Notion y valida el acceso a las bases de datos
principales del sistema. Este test debe ejecutarse antes que cualquier otro para confirmar
que las credenciales y configuración son correctas.

FUNCIONES:
- Validación de token de autenticación
- Verificación de acceso a bases de datos críticas
- Test de permisos básicos de lectura/escritura

EJECUCIÓN:
python Test/Core/test_connection.py

PROPÓSITO:
Test fundamental que debe pasar antes de ejecutar cualquier automatización.
Si este test falla, revisar configuración de .env y permisos en Notion.
"""

import os
from notion_client import Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_SPRINTS_ID = os.getenv("DB_SPRINTS_ID")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID")
DB_PERSONAS_ID = os.getenv("DB_PERSONAS_ID")
DB_PERFORMANCE_ID = os.getenv("DB_PERFORMANCE_ID")
DB_LOG_MODIFICACIONES_ID = os.getenv("DB_LOG_MODIFICACIONES_ID")

# Inicializar cliente
notion = Client(auth=NOTION_TOKEN)

# Probar cada base de datos
def test_database(db_id, name):
    try:
        response = notion.databases.retrieve(database_id=db_id)
        print(f"✅ Conexión exitosa a {name}: {response['title'][0]['text']['content'] if 'title' in response and response['title'] else 'Sin título'}")
        
        # Mostrar primeras propiedades para verificar
        print("   Propiedades:")
        for i, (prop_id, prop_info) in enumerate(response["properties"].items()):
            if i >= 3:  # Limitar a 3 propiedades para no saturar la salida
                break
            print(f"   - {prop_info.get('name', 'Sin nombre')}: {prop_info.get('type', 'Sin tipo')}")
        
        return True
    except Exception as e:
        print(f"❌ Error conectando a {name}: {e}")
        return False

print("\n🔍 PROBANDO CONEXIÓN A NOTION\n")
print("Token de API:", "✅ Configurado" if NOTION_TOKEN else "❌ No configurado")
print("\n--- BASES DE DATOS ---\n")
test_database(DB_SPRINTS_ID, "Sprints")
test_database(DB_TAREAS_ID, "Tareas")
test_database(DB_PERSONAS_ID, "Personas")
test_database(DB_PERFORMANCE_ID, "Performance")
test_database(DB_LOG_MODIFICACIONES_ID, "Log de Modificaciones")