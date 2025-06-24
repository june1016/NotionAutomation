#!/usr/bin/env python3
"""
Setup Monitoreo Inteligente - SNAPSHOT GLOBAL CORREGIDO
Crea snapshots de TODAS las tareas relevantes al configurar monitoreo
"""

import os
import logging
import json
from datetime import datetime, timezone, timedelta
from notion_client import Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_SPRINTS_ID = os.getenv("DB_SPRINTS_ID")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID")

notion = Client(auth=NOTION_TOKEN)

# ✅ CAMPOS MONITOREADOS OPTIMIZADOS (sin campos problemáticos)
PROPIEDADES_MONITOREADAS = [
    "Nombre",      # Título de la tarea
    "Personas",    # Responsables (solo si se elimina el último)
    "Prioridad",   # Prioridad de la tarea  
    "Tamaño",      # Tamaño estimado
    "Estado"       # Estado (siempre permitido pero se registra)
]

class MonitoringSetupInteligente:
    """Configurador de monitoreo inteligente con SNAPSHOT GLOBAL"""
    
    def __init__(self):
        self.zona_horaria = timezone(timedelta(hours=-5))
    
    def obtener_sprints_relevantes(self):
        """Obtiene sprints que deben monitorearse: actual + hasta 2 anteriores"""
        try:
            # Obtener todos los sprints ordenados por fecha fin (descendente)
            response = notion.databases.query(
                database_id=DB_SPRINTS_ID,
                sorts=[
                    {
                        "property": "Fecha Fin",
                        "direction": "descending"
                    }
                ]
            )
            
            sprints = response["results"]
            logger.info(f"Total de sprints encontrados: {len(sprints)}")
            
            sprints_relevantes = []
            
            # BUSCAR SPRINT ACTUAL
            sprint_actual = None
            for sprint in sprints:
                nombre_sprint = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
                es_actual_prop = sprint["properties"].get("Es Actual", {})
                
                es_actual_value = False
                if "formula" in es_actual_prop and es_actual_prop["formula"]:
                    if "boolean" in es_actual_prop["formula"]:
                        es_actual_value = es_actual_prop["formula"]["boolean"]
                
                if es_actual_value:
                    sprint_actual = sprint
                    logger.info(f"✅ Sprint actual encontrado: {nombre_sprint}")
                    break
            
            if not sprint_actual:
                logger.error("❌ No se encontró sprint actual")
                return []
            
            # Agregar sprint actual
            sprints_relevantes.append(sprint_actual)
            
            # Obtener fecha fin para comparación
            fecha_fin_actual_prop = sprint_actual["properties"].get("Fecha Fin", {})
            if "date" not in fecha_fin_actual_prop or not fecha_fin_actual_prop["date"]:
                logger.warning("⚠️ Sprint actual sin fecha fin - solo monitoreando sprint actual")
                return sprints_relevantes
            
            fecha_fin_actual_str = fecha_fin_actual_prop["date"]["start"]
            fecha_fin_actual = datetime.fromisoformat(fecha_fin_actual_str)
            
            # BUSCAR SPRINTS ANTERIORES (hasta 2 adicionales)
            sprints_anteriores_candidatos = []
            
            for sprint in sprints:
                if sprint["id"] == sprint_actual["id"]:
                    continue
                
                fecha_fin_prop = sprint["properties"].get("Fecha Fin", {})
                
                if "date" in fecha_fin_prop and fecha_fin_prop["date"]:
                    fecha_fin_str = fecha_fin_prop["date"]["start"]
                    fecha_fin = datetime.fromisoformat(fecha_fin_str)
                    
                    if fecha_fin < fecha_fin_actual:
                        nombre_sprint = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
                        sprints_anteriores_candidatos.append({
                            "sprint": sprint,
                            "nombre": nombre_sprint,
                            "fecha_fin": fecha_fin
                        })
            
            # Ordenar por fecha más reciente y tomar hasta 2
            sprints_anteriores_candidatos.sort(key=lambda x: x["fecha_fin"], reverse=True)
            max_anteriores = min(2, len(sprints_anteriores_candidatos))
            
            for i in range(max_anteriores):
                candidato = sprints_anteriores_candidatos[i]
                sprints_relevantes.append(candidato["sprint"])
                logger.info(f"✅ Sprint anterior encontrado: {candidato['nombre']}")
            
            logger.info(f"📊 Total sprints relevantes: {len(sprints_relevantes)}")
            return sprints_relevantes
            
        except Exception as e:
            logger.error(f"Error obteniendo sprints relevantes: {e}")
            return []
    
    def obtener_tareas_sprints_monitoreados(self, sprints_relevantes):
        """Obtiene todas las tareas válidas de los sprints monitoreados CON FILTRADO INTELIGENTE"""
        try:
            tareas_todas = []
            estadisticas_filtrado = {
                "total_consultadas": 0,
                "tareas_validas": 0,
                "excluidas_sin_nombre": 0,
                "excluidas_sin_personas": 0,
                "excluidas_sin_sprint": 0,
                "excluidas_multiples_razones": 0
            }
            
            for sprint in sprints_relevantes:
                sprint_id = sprint["id"]
                nombre_sprint = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
                
                logger.info(f"🔍 Obteniendo tareas del {nombre_sprint}...")
                
                # Implementar paginación
                has_more = True
                start_cursor = None
                tareas_sprint_bruto = []
                
                while has_more:
                    query_params = {
                        "database_id": DB_TAREAS_ID,
                        "filter": {
                            "property": "Sprint",
                            "relation": {
                                "contains": sprint_id
                            }
                        },
                        "page_size": 100
                    }
                    
                    if start_cursor:
                        query_params["start_cursor"] = start_cursor
                    
                    response = notion.databases.query(**query_params)
                    tareas_pagina = response["results"]
                    tareas_sprint_bruto.extend(tareas_pagina)
                    
                    has_more = response.get("has_more", False)
                    start_cursor = response.get("next_cursor")
                    
                    logger.debug(f"   📄 Página obtenida: {len(tareas_pagina)} tareas")
                
                # ✅ FILTRAR TAREAS VÁLIDAS
                tareas_sprint_validas = []
                estadisticas_sprint = {
                    "consultadas": len(tareas_sprint_bruto),
                    "validas": 0,
                    "excluidas": 0,
                    "detalles_exclusion": []
                }
                
                for tarea in tareas_sprint_bruto:
                    estadisticas_filtrado["total_consultadas"] += 1
                    
                    # Verificar validez de la tarea
                    resultado_validacion = self.validar_tarea_para_monitoreo(tarea)
                    
                    if resultado_validacion["es_valida"]:
                        tareas_sprint_validas.append(tarea)
                        estadisticas_filtrado["tareas_validas"] += 1
                        estadisticas_sprint["validas"] += 1
                    else:
                        estadisticas_sprint["excluidas"] += 1
                        estadisticas_sprint["detalles_exclusion"].append(resultado_validacion["razon"])
                        
                        # Contabilizar razones específicas
                        if "sin nombre" in resultado_validacion["razon"].lower():
                            estadisticas_filtrado["excluidas_sin_nombre"] += 1
                        if "sin personas" in resultado_validacion["razon"].lower():
                            estadisticas_filtrado["excluidas_sin_personas"] += 1
                        if "sin sprint" in resultado_validacion["razon"].lower():
                            estadisticas_filtrado["excluidas_sin_sprint"] += 1
                        if "múltiples" in resultado_validacion["razon"].lower():
                            estadisticas_filtrado["excluidas_multiples_razones"] += 1
                
                # Agregar tareas válidas al total
                tareas_todas.extend(tareas_sprint_validas)
                
                # Log detallado por sprint
                logger.info(f"   📋 Sprint {nombre_sprint}:")
                logger.info(f"      📥 Consultadas: {estadisticas_sprint['consultadas']}")
                logger.info(f"      ✅ Válidas: {estadisticas_sprint['validas']}")
                logger.info(f"      ❌ Excluidas: {estadisticas_sprint['excluidas']}")
                
                if estadisticas_sprint["excluidas"] > 0:
                    razones_agrupadas = {}
                    for razon in estadisticas_sprint["detalles_exclusion"]:
                        razones_agrupadas[razon] = razones_agrupadas.get(razon, 0) + 1
                    
                    for razon, cantidad in razones_agrupadas.items():
                        logger.info(f"         • {razon}: {cantidad}")
            
            # ✅ LOG CONSOLIDADO FINAL
            logger.info("=" * 50)
            logger.info("📊 ESTADÍSTICAS DE FILTRADO CONSOLIDADAS")
            logger.info("=" * 50)
            logger.info(f"📥 Total tareas consultadas: {estadisticas_filtrado['total_consultadas']}")
            logger.info(f"✅ Tareas válidas para monitoreo: {estadisticas_filtrado['tareas_validas']}")
            logger.info(f"❌ Total excluidas: {estadisticas_filtrado['total_consultadas'] - estadisticas_filtrado['tareas_validas']}")
            logger.info("")
            logger.info("🔍 DETALLES DE EXCLUSIONES:")
            logger.info(f"   • Sin nombre: {estadisticas_filtrado['excluidas_sin_nombre']}")
            logger.info(f"   • Sin personas: {estadisticas_filtrado['excluidas_sin_personas']}")
            logger.info(f"   • Sin sprint: {estadisticas_filtrado['excluidas_sin_sprint']}")
            logger.info(f"   • Múltiples razones: {estadisticas_filtrado['excluidas_multiples_razones']}")
            logger.info("=" * 50)
            
            return tareas_todas
            
        except Exception as e:
            logger.error(f"Error obteniendo tareas: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def validar_tarea_para_monitoreo(self, tarea):
        """Valida si una tarea debe ser incluida en el monitoreo"""
        try:
            problemas = []
            
            # 1. Verificar Nombre (no debe estar vacío)
            nombre = self.get_property_value(tarea, "Nombre")
            if not nombre or nombre.strip() == "":
                problemas.append("sin nombre")
            
            # 2. Verificar Personas (debe tener al menos una persona asignada)
            personas = self.get_property_value(tarea, "Personas")
            if not personas or (isinstance(personas, list) and len(personas) == 0):
                problemas.append("sin personas")
            
            # 3. Verificar Sprint (debe tener sprint asignado)
            sprint = self.get_property_value(tarea, "Sprint")
            if not sprint or (isinstance(sprint, list) and len(sprint) == 0):
                problemas.append("sin sprint")
            
            # Determinar resultado
            if not problemas:
                return {
                    "es_valida": True,
                    "razon": "Tarea válida"
                }
            else:
                if len(problemas) == 1:
                    razon = f"Excluida: {problemas[0]}"
                else:
                    razon = f"Excluida: múltiples razones ({', '.join(problemas)})"
                
                return {
                    "es_valida": False,
                    "razon": razon
                }
                
        except Exception as e:
            return {
                "es_valida": False,
                "razon": f"Error validando: {str(e)}"
            }
    
    def get_property_value(self, tarea, property_name):
        """Extrae valor de propiedad de manera robusta"""
        try:
            prop = tarea["properties"].get(property_name, {})
            
            if "title" in prop and prop["title"]:
                return prop["title"][0]["text"]["content"]
            elif "status" in prop and prop["status"]:
                return prop["status"]["name"]
            elif "select" in prop and prop["select"]:
                return prop["select"]["name"]
            elif "date" in prop and prop["date"]:
                return prop["date"]["start"]
            elif "relation" in prop:
                return [rel["id"] for rel in prop["relation"]]
            elif "rich_text" in prop and prop["rich_text"]:
                return prop["rich_text"][0]["text"]["content"]
            
            return None
        except Exception:
            return None
    
    def get_fecha_actual_gmt5(self):
        """Obtiene fecha actual en GMT-5 formato ISO"""
        colombia_tz = timezone(timedelta(hours=-5))
        fecha_colombia = datetime.now(colombia_tz)
        fecha_utc = fecha_colombia.astimezone(timezone.utc)
        return fecha_utc.isoformat().replace('+00:00', 'Z')
    
    def crear_snapshot_global(self, tareas_monitoreadas):
        """Crea snapshot global de TODAS las tareas que serán monitoreadas"""
        try:
            logger.info("📸 Creando snapshot global de todas las tareas monitoreadas...")
            
            snapshots_globales = {}
            timestamp_global = self.get_fecha_actual_gmt5()
            
            for tarea in tareas_monitoreadas:
                tarea_id = tarea["id"]
                nombre_tarea = self.get_property_value(tarea, "Nombre") or "Sin nombre"
                
                # Crear snapshot completo
                snapshot = {
                    "timestamp": timestamp_global,
                    "last_edited_time": tarea.get("last_edited_time"),
                    "nombre_tarea": nombre_tarea
                }
                
                # Agregar todas las propiedades monitoreadas
                for propiedad in PROPIEDADES_MONITOREADAS:
                    snapshot[propiedad] = self.get_property_value(tarea, propiedad)
                
                snapshots_globales[tarea_id] = snapshot
                logger.debug(f"   📸 Snapshot creado: {nombre_tarea}")
            
            # Guardar snapshots globales
            with open("task_snapshots.json", "w", encoding="utf-8") as f:
                json.dump(snapshots_globales, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Snapshot global creado: {len(snapshots_globales)} tareas")
            logger.info(f"🕒 Timestamp global: {timestamp_global}")
            
            return len(snapshots_globales)
            
        except Exception as e:
            logger.error(f"Error creando snapshot global: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    def configurar_monitoreo_inteligente(self):
        """Configura monitoreo completo con snapshot global"""
        logger.info("🧠 Configurando monitoreo inteligente con snapshot global...")
        
        try:
            # 1. Obtener sprints relevantes
            sprints_relevantes = self.obtener_sprints_relevantes()
            
            if not sprints_relevantes:
                logger.error("❌ No se encontraron sprints relevantes")
                return False
            
            # 2. Desactivar monitoreo en TODOS los sprints
            response = notion.databases.query(database_id=DB_SPRINTS_ID)
            todos_sprints = response["results"]
            
            logger.info(f"🔄 Desactivando monitoreo en {len(todos_sprints)} sprints...")
            
            for sprint in todos_sprints:
                try:
                    notion.pages.update(
                        page_id=sprint["id"],
                        properties={
                            "Monitoreo Activo": {"checkbox": False}
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error desactivando monitoreo: {e}")
            
            # 3. Activar monitoreo solo en sprints relevantes
            logger.info(f"✅ Activando monitoreo en {len(sprints_relevantes)} sprints relevantes...")
            
            for sprint in sprints_relevantes:
                try:
                    notion.pages.update(
                        page_id=sprint["id"],
                        properties={
                            "Monitoreo Activo": {"checkbox": True}
                        }
                    )
                    
                    nombre = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
                    
                    # Determinar tipo
                    es_actual_prop = sprint["properties"].get("Es Actual", {})
                    es_actual_value = False
                    
                    if "formula" in es_actual_prop and es_actual_prop["formula"]:
                        if "boolean" in es_actual_prop["formula"]:
                            es_actual_value = es_actual_prop["formula"]["boolean"]
                    
                    tipo = "ACTUAL" if es_actual_value else "ANTERIOR"
                    logger.info(f"  ✅ {nombre} ({tipo})")
                    
                except Exception as e:
                    logger.error(f"Error activando monitoreo: {e}")
            
            # 4. ✅ NUEVO: Obtener todas las tareas de sprints monitoreados
            tareas_monitoreadas = self.obtener_tareas_sprints_monitoreados(sprints_relevantes)
            
            if not tareas_monitoreadas:
                logger.warning("⚠️ No se encontraron tareas para monitorear")
                return False
            
            # 5. ✅ NUEVO: Crear snapshot global
            total_snapshots = self.crear_snapshot_global(tareas_monitoreadas)
            
            if total_snapshots == 0:
                logger.error("❌ Error creando snapshots globales")
                return False
            
            logger.info("=" * 60)
            logger.info("✅ CONFIGURACIÓN COMPLETADA CON SNAPSHOT GLOBAL")
            logger.info(f"📊 Sprints monitoreados: {len(sprints_relevantes)}")
            logger.info(f"📋 Tareas con snapshot: {total_snapshots}")
            logger.info(f"🔧 Campos monitoreados: {', '.join(PROPIEDADES_MONITOREADAS)}")
            logger.info("🚀 Sistema listo para monitoreo en tiempo real")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Error en configuración de monitoreo: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def main():
    """Función principal"""
    setup = MonitoringSetupInteligente()
    
    if setup.configurar_monitoreo_inteligente():
        logger.info("🎉 Sistema configurado exitosamente")
        exit(0)
    else:
        logger.error("❌ Error en configuración del sistema")
        exit(1)

if __name__ == "__main__":
    main()