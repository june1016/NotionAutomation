"""
Sistema de Automatización de Cierre de Sprint v2.0
===================================================

Este script automatiza el proceso completo de cierre de sprint y apertura del siguiente:

FUNCIONES PRINCIPALES:
1. Detecta el sprint que debe cerrarse usando validación híbrida (fecha local + fórmula Notion)
2. Captura métricas de performance de cada persona del equipo
3. Filtra tareas imprevistas no completadas para métricas justas
4. Cierra el sprint actual y activa automáticamente el siguiente
5. Establece relaciones bidireccionales entre Performance ↔ Tareas

EJECUCIÓN RECOMENDADA:
- Horario: 6:00 PM Colombia (evita problemas de zona horaria)
- Frecuencia: Cada 15 días (último día del sprint)
- Ambiente: AWS Lambda con cron schedule

DISEÑO:
- Sistema híbrido resistente a fallos de zona horaria
- Logging detallado para debugging en producción
- Validaciones múltiples para robustez
- Optimizado para rendimiento y limpieza de código
"""

import os
import logging
import re
from datetime import datetime, timedelta
import pytz
from notion_client import Client
from dotenv import load_dotenv

__all__ = ['ejecutar_cierre_sprint', 'crear_solo_nuevo_sprint']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sprint_automation.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_SPRINTS_ID = os.getenv("DB_SPRINTS_ID")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID") 
DB_PERSONAS_ID = os.getenv("DB_PERSONAS_ID")
DB_PERFORMANCE_ID = os.getenv("DB_PERFORMANCE_ID")

notion = Client(auth=NOTION_TOKEN)

def obtener_sprint_para_cierre():
    """
    Detecta el sprint que debe cerrarse usando validación híbrida.
    Prioriza fecha local sobre fórmula Notion para evitar problemas de zona horaria.
    """
    try:
        colombia_tz = pytz.timezone('America/Bogota')
        ahora_colombia = datetime.now(colombia_tz)
        fecha_hoy = ahora_colombia.date()

        logger.info(f"🕒 Ejecutando a las {ahora_colombia.strftime('%H:%M:%S')} hora Colombia")
        logger.info(f"📅 Fecha local: {fecha_hoy.strftime('%Y-%m-%d')}")

        response = notion.databases.query(
            database_id=DB_SPRINTS_ID,
            filter={"property": "Estado", "status": {"equals": "En curso"}}
        )

        for sprint in response["results"]:
            try:
                props = sprint["properties"]
                nombre = props["Nombre"]["title"][0]["text"]["content"]
                fecha_fin = datetime.fromisoformat(props["Fecha Fin"]["date"]["start"]).date()

                if fecha_fin == fecha_hoy:
                    logger.info(f"✅ Sprint para cerrar: {nombre} (finaliza hoy)")
                    return sprint
                elif fecha_fin == (fecha_hoy - timedelta(days=1)):
                    logger.warning(f"⚠️ Ejecución tardía: {nombre} finalizó ayer")
                    return sprint
            except Exception as e:
                logger.error(f"Error procesando sprint: {e}")

        logger.warning("⚠️ Usando fórmula Notion como fallback...")
        response_formula = notion.databases.query(
            database_id=DB_SPRINTS_ID,
            filter={"property": "Es Actual", "formula": {"checkbox": {"equals": True}}}
        )
        
        if response_formula["results"]:
            return response_formula["results"][0]

        if response["results"]:
            logger.warning("⚠️ Usando primer sprint 'En curso' como último recurso")
            return response["results"][0]

        logger.error("❌ CRÍTICO: No se encontró sprint para cerrar")
        return None

    except Exception as e:
        logger.critical(f"Error crítico en detección de sprint: {e}")
        return None

def obtener_tareas_del_sprint(sprint_id):
    """Obtiene todas las tareas del sprint con paginación automática"""
    tareas = []
    next_cursor = None
    
    while True:
        response = notion.databases.query(
            database_id=DB_TAREAS_ID,
            filter={"property": "Sprint", "relation": {"contains": sprint_id}},
            start_cursor=next_cursor,
            page_size=100
        )
        tareas.extend(response["results"])
        next_cursor = response.get("next_cursor")
        if not next_cursor:
            break
            
    logger.info(f"Encontradas {len(tareas)} tareas para el sprint")
    return tareas

def agrupar_tareas_por_persona(tareas):
    """Agrupa tareas por persona, reporta tareas sin asignar"""
    personas = {}
    tareas_sin_asignar = []
    
    for tarea in tareas:
        personas_asignadas = tarea["properties"].get("Personas", {}).get("relation", [])
        if not personas_asignadas:
            tareas_sin_asignar.append(tarea)
            continue
            
        for persona_rel in personas_asignadas:
            pid = persona_rel["id"]
            personas.setdefault(pid, []).append(tarea)
    
    if tareas_sin_asignar:
        logger.warning(f"Hay {len(tareas_sin_asignar)} tareas sin asignar")
    
    return personas, tareas_sin_asignar

def filtrar_tareas_para_metricas(tareas):
    """
    Filtra tareas excluyendo imprevistas no completadas.
    Solo penaliza tareas planificadas, no eventos inesperados.
    """
    tareas_filtradas = []
    tareas_excluidas = []
    
    for tarea in tareas:
        props = tarea["properties"]
        prioridad = (props.get("Prioridad", {}).get("select") or {}).get("name", "").lower()
        estado = (props.get("Estado", {}).get("status") or {}).get("name", "")
        
        es_imprevista_incompleta = (prioridad == "imprevista" and estado != "Listo")
        
        if es_imprevista_incompleta:
            try:
                nombre = props["Nombre"]["title"][0]["text"]["content"]
            except:
                nombre = "Sin nombre"
            tareas_excluidas.append({"nombre": nombre, "razon": "Imprevista no completada"})
        else:
            tareas_filtradas.append(tarea)

    return tareas_filtradas, tareas_excluidas

def obtener_info_persona(persona_id):
    """Obtiene información de persona con manejo de errores"""
    try:
        return notion.pages.retrieve(persona_id)
    except Exception as e:
        logger.error(f"Error obteniendo persona {persona_id}: {e}")
        return None

def obtener_departamento_persona(persona_info):
    """Extrae departamento de persona buscando en múltiples propiedades posibles"""
    try:
        props = persona_info["properties"]
        
        for prop_name in ["Área", "Area", "Departamento", "Depto"]:
            if prop_name not in props:
                continue
            prop = props[prop_name]
            if prop.get("type") != "relation" or not prop.get("relation"):
                continue
                
            dept_id = prop["relation"][0]["id"]
            dept_info = notion.pages.retrieve(dept_id)
            title_list = dept_info["properties"].get("Nombre", {}).get("title", [])
            
            if title_list:
                return title_list[0]["text"]["content"]
        
        return "Sin departamento asignado"
        
    except Exception as e:
        logger.error(f"Error obteniendo departamento: {e}")
        return "Error al obtener departamento"

def calcular_metricas_persona(tareas_filtradas):
    """Calcula métricas de performance basadas en tareas filtradas"""
    carga_asignada = carga_completada = tareas_completadas = 0
    
    for tarea in tareas_filtradas:
        props = tarea["properties"]
        
        try:
            carga_asignada += float(props.get("Carga", {}).get("formula", {}).get("number") or 0)
        except:
            pass
        try:
            carga_completada += float(props.get("Carga Completada", {}).get("formula", {}).get("number") or 0)
        except:
            pass
        try:
            tareas_completadas += int(props.get("Completada", {}).get("formula", {}).get("number") or 0)
        except:
            pass
    
    return {
        "carga_asignada": carga_asignada,
        "carga_completada": carga_completada,
        "tareas_totales": len(tareas_filtradas),
        "tareas_completadas": tareas_completadas
    }

def verificar_performance_existente(persona_id, sprint_id):
    """Verifica si ya existe registro de performance para esta combinación"""
    response = notion.databases.query(
        database_id=DB_PERFORMANCE_ID,
        filter={
            "and": [
                {"property": "Persona", "relation": {"contains": persona_id}},
                {"property": "Sprint", "relation": {"contains": sprint_id}}
            ]
        }
    )
    return bool(response["results"])

def crear_registro_performance(persona_id, sprint_id, sprint_info, tareas):
    """
    Crea registro de performance y establece relaciones bidireccionales.
    
    NOTA: Los porcentajes y score se calculan automáticamente en Notion via fórmulas,
    solo enviamos los valores base (carga asignada, completada, tareas totales, completadas).
    """
    if verificar_performance_existente(persona_id, sprint_id):
        logger.warning("Performance ya existe para esta persona-sprint")
        return None

    persona_info = obtener_info_persona(persona_id)
    if not persona_info:
        return None

    try:
        persona_nombre = persona_info["properties"]["Nombre"]["title"][0]["text"]["content"]
        sprint_nombre = sprint_info["properties"]["Nombre"]["title"][0]["text"]["content"]
    except:
        logger.error("Error extrayendo nombres de persona/sprint")
        return None

    departamento = obtener_departamento_persona(persona_info)
    tareas_filtradas, tareas_excluidas = filtrar_tareas_para_metricas(tareas)
    
    if tareas_excluidas:
        logger.info(f"Excluidas {len(tareas_excluidas)} imprevistas no completadas para {persona_nombre}")
    
    metricas = calcular_metricas_persona(tareas_filtradas)
    tareas_ids = [{"id": tarea["id"]} for tarea in tareas]

    try:
        response = notion.pages.create(
            parent={"database_id": DB_PERFORMANCE_ID},
            properties={
                "Nombre": {"title": [{"text": {"content": f"{persona_nombre} - {sprint_nombre}"}}]},
                "Persona": {"relation": [{"id": persona_id}]},
                "Sprint": {"relation": [{"id": sprint_id}]},
                "Área": {"rich_text": [{"text": {"content": departamento}}]},
                "Tareas Vinculadas": {"relation": tareas_ids},
                "Carga Asignada": {"number": metricas["carga_asignada"]},
                "Carga Completada": {"number": metricas["carga_completada"]},
                "Tareas Totales": {"number": metricas["tareas_totales"]},
                "Tareas Completadas": {"number": metricas["tareas_completadas"]},
                "Fecha Captura": {"date": {"start": datetime.now().isoformat()}},
                "Estado": {"select": {"name": "Cerrado"}}
            }
        )

        performance_id = response["id"]
        logger.info(f"✅ Performance creado para {persona_nombre}")

        for tarea in tareas:
            notion.pages.update(
                page_id=tarea["id"],
                properties={"Performance Vinculada": {"relation": [{"id": performance_id}]}}
            )

        return response

    except Exception as e:
        logger.error(f"Error creando performance para {persona_nombre}: {e}")
        return None

def finalizar_sprint(sprint_id):
    """Marca sprint como finalizado"""
    try:
        notion.pages.update(
            page_id=sprint_id,
            properties={"Estado": {"status": {"name": "Finalizado"}}}
        )
        logger.info("✅ Sprint marcado como Finalizado")
        return True
    except Exception as e:
        logger.error(f"Error finalizando sprint: {e}")
        return False

def obtener_numero_sprint(nombre_sprint):
    """Extrae número de sprint del nombre usando regex"""
    match = re.search(r'Sprint\s*(\d+)', nombre_sprint, re.IGNORECASE)
    return int(match.group(1)) if match else None

def buscar_sprint_por_numero(numero):
    """Busca sprint por número específico"""
    try:
        response = notion.databases.query(
            database_id=DB_SPRINTS_ID,
            filter={"property": "Nombre", "title": {"contains": f"Sprint {numero}"}}
        )
        return response["results"][0] if response["results"] else None
    except Exception as e:
        logger.error(f"Error buscando Sprint {numero}: {e}")
        return None

def activar_sprint_siguiente(sprint, numero):
    """Activa sprint existente o crea uno nuevo"""
    nombre = f"Sprint {numero}"
    
    if sprint:
        logger.info(f"Activando {nombre} existente...")
        try:
            notion.pages.update(
                page_id=sprint["id"],
                properties={
                    "Estado": {"status": {"name": "En curso"}},
                    "Monitoreo Activo": {"checkbox": True}
                }
            )
            logger.info(f"✅ {nombre} activado correctamente")
            return sprint
        except Exception as e:
            logger.error(f"Error activando {nombre}: {e}")
            return None
    
    logger.info(f"Creando {nombre} nuevo...")
    return None

def crear_sprint_nuevo(sprint_actual, numero_nuevo):
    """Crea nuevo sprint con fechas calculadas"""
    try:
        fecha_fin_actual = sprint_actual["properties"]["Fecha Fin"]["date"]["start"]
        fecha_fin_dt = datetime.fromisoformat(fecha_fin_actual.replace('Z', '+00:00'))
        
        fecha_inicio = fecha_fin_dt + timedelta(days=1)
        fecha_fin = fecha_inicio + timedelta(days=14)
        
        response = notion.pages.create(
            parent={"database_id": DB_SPRINTS_ID},
            properties={
                "Nombre": {"title": [{"text": {"content": f"Sprint {numero_nuevo}"}}]},
                "Fecha Inicio": {"date": {"start": fecha_inicio.strftime('%Y-%m-%d')}},
                "Fecha Fin": {"date": {"start": fecha_fin.strftime('%Y-%m-%d')}},
                "Estado": {"status": {"name": "En curso"}},
                "Monitoreo Activo": {"checkbox": True}
            }
        )
        
        logger.info(f"✅ Sprint {numero_nuevo} creado exitosamente")
        return response
        
    except Exception as e:
        logger.error(f"Error creando Sprint {numero_nuevo}: {e}")
        return None

def gestionar_sprint_siguiente(sprint_actual):
    """Gestiona la transición al siguiente sprint (activar existente o crear nuevo)"""
    numero_actual = obtener_numero_sprint(sprint_actual["properties"]["Nombre"]["title"][0]["text"]["content"])
    if not numero_actual:
        logger.error("No se pudo determinar número de sprint actual")
        return None
    
    numero_siguiente = numero_actual + 1
    sprint_siguiente = buscar_sprint_por_numero(numero_siguiente)
    
    if sprint_siguiente:
        return activar_sprint_siguiente(sprint_siguiente, numero_siguiente)
    else:
        return crear_sprint_nuevo(sprint_actual, numero_siguiente)

def ejecutar_cierre_sprint():
    """
    Función principal: ejecuta el proceso completo de cierre de sprint.
    
    FLUJO:
    1. Detecta sprint a cerrar
    2. Obtiene y agrupa tareas por persona  
    3. Crea registros de performance con métricas filtradas
    4. Finaliza sprint actual
    5. Activa o crea sprint siguiente
    """
    logger.info("🚀 Iniciando cierre de sprint - Sistema Híbrido v2.0")

    sprint = obtener_sprint_para_cierre()
    if not sprint:
        logger.error("❌ No se encontró sprint para cerrar")
        return False

    try:
        sprint_id = sprint["id"]
        nombre = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
        fecha_fin = sprint["properties"]["Fecha Fin"]["date"]["start"]
        
        logger.info(f"📊 Sprint a cerrar: {nombre} (finaliza: {fecha_fin})")
        
    except Exception as e:
        logger.error(f"Error validando sprint: {e}")
        return False

    tareas = obtener_tareas_del_sprint(sprint_id)
    personas, _ = agrupar_tareas_por_persona(tareas)

    if not personas:
        logger.warning("⚠️ No hay tareas asignadas a personas")
        return False

    registros_creados = 0
    for persona_id, tareas_persona in personas.items():
        if crear_registro_performance(persona_id, sprint_id, sprint, tareas_persona):
            registros_creados += 1

    if registros_creados == 0:
        logger.warning("⚠️ No se crearon registros de performance")
        return False

    if not finalizar_sprint(sprint_id):
        logger.error("❌ Error finalizando sprint")
        return False

    logger.info(f"🏁 {registros_creados} registros de performance creados")
    
    sprint_siguiente = gestionar_sprint_siguiente(sprint)
    if sprint_siguiente:
        logger.info("✅ Proceso completo: Sprint cerrado y siguiente activado")
        return True
    else:
        logger.warning("⚠️ Sprint cerrado pero problema con el siguiente")
        return True

def crear_solo_nuevo_sprint():
    """Función auxiliar para crear solo el siguiente sprint sin cerrar actual"""
    logger.info("🔄 Creando solo nuevo sprint")
    
    sprint_actual = obtener_sprint_para_cierre()
    if not sprint_actual:
        logger.error("❌ No hay sprint actual")
        return False
    
    return bool(gestionar_sprint_siguiente(sprint_actual))

def verificar_si_hay_cierre_hoy():
    """
    Verifica si HOY es día de cierre de sprint sin ejecutar el cierre.
    Retorna True solo si hay un sprint que realmente finaliza hoy.
    """
    try:
        colombia_tz = pytz.timezone('America/Bogota')
        fecha_hoy = datetime.now(colombia_tz).date()
        
        # Buscar sprints En curso
        response = notion.databases.query(
            database_id=DB_SPRINTS_ID,
            filter={"property": "Estado", "status": {"equals": "En curso"}}
        )
        
        for sprint in response["results"]:
            try:
                props = sprint["properties"]
                nombre = props["Nombre"]["title"][0]["text"]["content"]
                fecha_fin = datetime.fromisoformat(props["Fecha Fin"]["date"]["start"]).date()
                
                # ¿Este sprint finaliza exactamente HOY?
                if fecha_fin == fecha_hoy:
                    logger.info(f"📅 Día de cierre detectado: {nombre} finaliza hoy ({fecha_hoy})")
                    return True, sprint
                
                # Tolerancia de 1 día por ejecución tardía  
                elif fecha_fin == (fecha_hoy - timedelta(days=1)):
                    logger.info(f"📅 Cierre tardío detectado: {nombre} finalizó ayer ({fecha_fin})")
                    return True, sprint
                    
            except Exception as e:
                logger.error(f"Error verificando sprint {sprint.get('id', 'unknown')}: {e}")
                continue
        
        # No hay sprint que finalice hoy
        return False, None
        
    except Exception as e:
        logger.error(f"Error en verificación de cierre: {e}")
        return False, None

def main_ejecucion_diaria():
    """
    Función principal para ejecución diaria en AWS.
    Solo ejecuta cierre si realmente es día de cierre.
    """
    try:
        colombia_tz = pytz.timezone('America/Bogota')
        ahora = datetime.now(colombia_tz)
        
        print(f"🕒 Verificación diaria - {ahora.strftime('%Y-%m-%d %H:%M:%S')} Colombia")
        
        # Verificar si HOY es día de cierre
        hay_cierre, sprint = verificar_si_hay_cierre_hoy()
        
        if not hay_cierre:
            print("📅 No hay cierre de sprint programado para hoy")
            print("✅ Verificación completada - No se requiere acción")
            return True
        
        # Solo si HAY cierre, ejecutar el proceso completo
        print("🚀 Día de cierre detectado - Iniciando proceso...")
        logger.info("=" * 60)
        logger.info("🎯 EJECUCIÓN DE CIERRE DE SPRINT")
        logger.info("=" * 60)
        
        return ejecutar_cierre_sprint()
        
    except Exception as e:
        logger.critical(f"Error crítico en ejecución diaria: {e}")
        print(f"❌ Error crítico: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "--crear-sprint":
                resultado = crear_solo_nuevo_sprint()
                print("✅ Sprint creado" if resultado else "❌ Error creando sprint")
            elif sys.argv[1] == "--daily":
                resultado = main_ejecucion_diaria()
                exit(0 if resultado else 1)
            elif sys.argv[1] == "--check":
                hay_cierre, sprint = verificar_si_hay_cierre_hoy()
                if hay_cierre:
                    nombre = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
                    fecha_fin = sprint["properties"]["Fecha Fin"]["date"]["start"]
                    print(f"✅ Cierre programado: {nombre} (finaliza: {fecha_fin})")
                else:
                    print("📅 No hay cierre programado para hoy")
                exit(0)
            else:
                print("❌ Argumento no reconocido. Uso: --daily | --check | --crear-sprint")
                exit(1)
        else:
            # Ejecución manual normal (para testing)
            resultado = ejecutar_cierre_sprint()
            print("✅ Proceso completo" if resultado else "❌ Error en proceso")
            
    except Exception as e:
        logger.critical(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")
        exit(1)