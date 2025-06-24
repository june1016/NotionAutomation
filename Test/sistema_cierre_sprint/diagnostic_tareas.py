"""
Diagnóstico de Estructura de Tareas
===================================

Analiza en profundidad la estructura y propiedades de las tareas para identificar
problemas de formato, propiedades faltantes o inconsistencias en los datos.
Especialmente útil para debugging de problemas con fórmulas y cálculos.

FUNCIONES:
- Inspección detallada de propiedades de tareas
- Verificación de estructura de datos de Notion
- Test de manejo seguro de propiedades None
- Análisis de consistencia en tipos de datos

EJECUCIÓN:
python Test/SistemaCierreSprint/diagnostic_tareas.py

CASOS DE USO:
- Troubleshooting de errores en cálculo de métricas
- Verificación tras cambios en estructura de BD Tareas
- Análisis de problemas con fórmulas de Notion
"""
import os
import sys
import json
import logging
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [DIAGNOSTIC] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID") 

# Inicializar cliente de Notion
notion = Client(auth=NOTION_TOKEN)

def diagnosticar_propiedades_tareas(sprint_id, max_tareas=5):
    """Diagnostica las propiedades de las primeras tareas para identificar problemas"""
    logger.info(f"🔍 Diagnosticando propiedades de tareas del sprint {sprint_id}")
    
    # Obtener primeras tareas
    response = notion.databases.query(
        database_id=DB_TAREAS_ID,
        filter={
            "property": "Sprint",
            "relation": {
                "contains": sprint_id
            }
        },
        page_size=max_tareas
    )
    
    tareas = response["results"]
    logger.info(f"📊 Analizando {len(tareas)} tareas...")
    
    for i, tarea in enumerate(tareas):
        logger.info(f"\n📄 === TAREA {i+1} ===")
        logger.info(f"ID: {tarea['id']}")
        
        props = tarea.get("properties", {})
        logger.info(f"Propiedades disponibles: {list(props.keys())}")
        
        # Analizar propiedades críticas
        propiedades_criticas = {
            "Nombre": "title",
            "Estado": "status", 
            "Prioridad": "select",
            "Carga": "formula",
            "Carga Completada": "formula",
            "Completada": "formula"
        }
        
        for prop_name, prop_type in propiedades_criticas.items():
            logger.info(f"\n  🔍 {prop_name}:")
            
            prop_value = props.get(prop_name)
            
            if prop_value is None:
                logger.warning(f"    ❌ Es None")
                continue
            
            if not isinstance(prop_value, dict):
                logger.warning(f"    ❌ No es dict: {type(prop_value)} = {prop_value}")
                continue
            
            logger.info(f"    ✅ Es dict con keys: {list(prop_value.keys())}")
            
            # Análisis específico por tipo
            if prop_type == "title":
                title_list = prop_value.get("title", [])
                if title_list and len(title_list) > 0:
                    texto = title_list[0].get("text", {}).get("content", "Sin contenido")
                    logger.info(f"    📝 Título: '{texto}'")
                else:
                    logger.warning(f"    ⚠️ Lista título vacía")
            
            elif prop_type == "status":
                status_info = prop_value.get("status")
                if status_info is None:
                    logger.warning(f"    ❌ status es None")
                else:
                    status_name = status_info.get("name", "Sin nombre")
                    logger.info(f"    📊 Estado: '{status_name}'")
            
            elif prop_type == "select":
                select_info = prop_value.get("select")
                if select_info is None:
                    logger.warning(f"    ❌ select es None")
                else:
                    select_name = select_info.get("name", "Sin nombre") if isinstance(select_info, dict) else str(select_info)
                    logger.info(f"    🎯 Selección: '{select_name}'")
            
            elif prop_type == "formula":
                formula_info = prop_value.get("formula")
                if formula_info is None:
                    logger.warning(f"    ❌ formula es None")
                else:
                    if isinstance(formula_info, dict):
                        formula_number = formula_info.get("number")
                        formula_type = formula_info.get("type")
                        logger.info(f"    🧮 Fórmula: number={formula_number}, type={formula_type}")
                    else:
                        logger.info(f"    🧮 Fórmula: {formula_info}")
            
            # Mostrar estructura completa si es pequeña
            if len(str(prop_value)) < 200:
                logger.info(f"    📋 Estructura completa: {json.dumps(prop_value, indent=6, ensure_ascii=False)}")

def test_manejo_seguro_propiedades(sprint_id):
    """Prueba el manejo seguro de propiedades None"""
    logger.info(f"\n🧪 Testing manejo seguro de propiedades...")
    
    # Obtener algunas tareas
    response = notion.databases.query(
        database_id=DB_TAREAS_ID,
        filter={
            "property": "Sprint",
            "relation": {
                "contains": sprint_id
            }
        },
        page_size=10
    )
    
    tareas = response["results"]
    
    for i, tarea in enumerate(tareas[:3]):
        logger.info(f"\n📄 TAREA {i+1} - Test de manejo seguro:")
        
        props = tarea["properties"]
        
        # Método ANTERIOR (problemático)
        try:
            estado_old = props.get("Estado", {}).get("status", {}).get("name", "Sin estado")
            logger.info(f"  ✅ Método anterior Estado: '{estado_old}'")
        except Exception as e:
            logger.error(f"  ❌ Método anterior Estado FALLÓ: {e}")
        
        # Método NUEVO (seguro)
        try:
            estado_prop = props.get("Estado") or {}
            status_prop = estado_prop.get("status") or {}
            estado_new = status_prop.get("name") or "Sin estado"
            logger.info(f"  ✅ Método nuevo Estado: '{estado_new}'")
        except Exception as e:
            logger.error(f"  ❌ Método nuevo Estado FALLÓ: {e}")
        
        # Test Prioridad
        try:
            prioridad_prop = props.get("Prioridad") or {}
            select_prop = prioridad_prop.get("select") or {}
            prioridad = select_prop.get("name") or "Sin prioridad"
            logger.info(f"  ✅ Método nuevo Prioridad: '{prioridad}'")
        except Exception as e:
            logger.error(f"  ❌ Método nuevo Prioridad FALLÓ: {e}")

if __name__ == "__main__":
    # Obtener el sprint actual automáticamente
    logger.info("🚀 Iniciando diagnóstico de tareas...")
    
    try:
        # Obtener sprint actual en lugar de usar ID hardcodeado
        logger.info("🔍 Obteniendo sprint actual...")
        response = notion.databases.query(
            database_id=os.getenv("DB_SPRINTS_ID"),
            filter={
                "property": "Es Actual",
                "formula": {
                    "checkbox": {
                        "equals": True
                    }
                }
            }
        )
        
        if not response["results"]:
            logger.error("❌ No se encontró sprint actual")
            exit(1)
        
        sprint_actual = response["results"][0]
        sprint_id = sprint_actual["id"]
        sprint_nombre = sprint_actual["properties"]["Nombre"]["title"][0]["text"]["content"]
        
        logger.info(f"✅ Sprint actual encontrado: {sprint_nombre} (ID: {sprint_id})")
        
        # Diagnóstico detallado
        diagnosticar_propiedades_tareas(sprint_id, max_tareas=3)
        
        # Test de manejo seguro
        test_manejo_seguro_propiedades(sprint_id)
        
        logger.info("\n✅ Diagnóstico completado")
        
    except Exception as e:
        logger.error(f"❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()