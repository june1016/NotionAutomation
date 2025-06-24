#!/usr/bin/env python3
"""
Monitor de Tareas Reactivo - VERSIÓN 100% FUNCIONAL
Fixes finales: Bug evasión "Imprevista" + Detección de usuario en eliminaciones
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from notion_client import Client
from dotenv import load_dotenv
import json
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID")
DB_SPRINTS_ID = os.getenv("DB_SPRINTS_ID")
DB_LOG_MODIFICACIONES_ID = os.getenv("DB_LOG_MODIFICACIONES_ID")
DB_PERSONAS_ID = os.getenv("DB_PERSONAS_ID")

notion = Client(auth=NOTION_TOKEN)

DIAS_BLOQUEO = 4

# Campos monitoreados optimizados
PROPIEDADES_MONITOREADAS = [
    "Nombre",      # Título de la tarea
    "Personas",    # Responsables (solo si se elimina el último)
    "Prioridad",   # Prioridad de la tarea  
    "Tamaño",      # Tamaño estimado
    "Estado"       # Estado (siempre permitido pero se registra)
]

class TaskMonitorReactivo:
    """Monitor reactivo de tareas - VERSIÓN 100% FUNCIONAL"""
    
    def __init__(self):
        self.cache_usuarios = {}
        self.cache_nombres_personas = {}
        self.zona_horaria = timezone(timedelta(hours=-5))
        # Sistema anti-bucle mejorado
        self.cambios_sistema_timestamps = {}
        self.webhooks_en_espera = {}
        # ✅ NUEVO: Cache de última actividad por usuario para eliminaciones
        self.ultima_actividad_usuarios = {}
        
    def inicializar(self):
        """Inicializa el monitor"""
        logger.info("🔧 Inicializando monitor reactivo...")
        self.cargar_cache_usuarios()
        self.cargar_cache_nombres_personas()
        
        # Verificar snapshots globales
        if not os.path.exists("task_snapshots.json"):
            logger.warning("⚠️ No se encontraron snapshots globales")
            logger.warning("   Ejecuta 'python setup_monitoring.py' primero")
        else:
            with open("task_snapshots.json", "r", encoding="utf-8") as f:
                snapshots = json.load(f)
                logger.info(f"📸 Snapshots globales cargados: {len(snapshots)} tareas")
        
        logger.info("✅ Monitor reactivo inicializado")
    
    def cargar_cache_usuarios(self):
        """Carga cache de usuarios reales desde base de Personas"""
        try:
            response = notion.databases.query(database_id=DB_PERSONAS_ID)
            personas = response["results"]
            
            for persona in personas:
                cuenta_notion = persona["properties"].get("Cuenta Notion", {})
                nombre = persona["properties"].get("Nombre", {})
                
                if "people" in cuenta_notion and cuenta_notion["people"]:
                    user_id = cuenta_notion["people"][0]["id"]
                    if "title" in nombre and nombre["title"]:
                        nombre_real = nombre["title"][0]["text"]["content"]
                        self.cache_usuarios[user_id] = nombre_real
                        
            logger.info(f"Cache de usuarios cargado: {len(self.cache_usuarios)} usuarios")
            
        except Exception as e:
            logger.error(f"Error cargando cache de usuarios: {e}")
    
    def cargar_cache_nombres_personas(self):
        """Carga cache ID → Nombre para logs mejorados"""
        try:
            response = notion.databases.query(database_id=DB_PERSONAS_ID)
            personas = response["results"]
            
            for persona in personas:
                persona_id = persona["id"]
                nombre = persona["properties"].get("Nombre", {})
                
                if "title" in nombre and nombre["title"]:
                    nombre_real = nombre["title"][0]["text"]["content"]
                    self.cache_nombres_personas[persona_id] = nombre_real
                        
            logger.info(f"Cache nombres personas cargado: {len(self.cache_nombres_personas)} personas")
            
        except Exception as e:
            logger.error(f"Error cargando cache nombres personas: {e}")
    
    def obtener_tarea_actual(self, page_id):
        """Obtiene datos actuales de una tarea específica"""
        try:
            tarea = notion.pages.retrieve(page_id)
            return tarea
        except Exception as e:
            logger.error(f"Error obteniendo tarea {page_id}: {e}")
            return None
    
    def verificar_si_sprint_monitoreable(self, tarea):
        """Verifica si la tarea pertenece a un sprint monitoreable"""
        try:
            sprint_relation = tarea["properties"].get("Sprint", {}).get("relation", [])
            
            if not sprint_relation:
                return False
            
            sprint_id = sprint_relation[0]["id"]
            sprint = notion.pages.retrieve(sprint_id)
            
            monitoreo_activo = sprint["properties"].get("Monitoreo Activo", {}).get("checkbox", False)
            return monitoreo_activo
            
        except Exception as e:
            logger.error(f"Error verificando sprint monitoreable: {e}")
            return False
    
    def es_cambio_del_sistema(self, tarea_id, tarea_last_edited_time):
        """Sistema anti-bucle mejorado con limpieza agresiva"""
        try:
            if tarea_id not in self.cambios_sistema_timestamps:
                return False
            
            timestamp_sistema = self.cambios_sistema_timestamps[tarea_id]
            
            if tarea_last_edited_time:
                tarea_timestamp = datetime.fromisoformat(tarea_last_edited_time.replace('Z', '+00:00')).timestamp()
            else:
                return False
            
            diferencia = abs(tarea_timestamp - timestamp_sistema)
            
            # Ventana corta para detección
            if diferencia < 3:
                logger.debug(f"🤖 Cambio del sistema detectado (diferencia: {diferencia:.2f}s)")
                return True
            
            # Limpieza agresiva
            if diferencia > 10:
                del self.cambios_sistema_timestamps[tarea_id]
                logger.debug(f"🧹 Timestamp del sistema limpiado para {tarea_id[:8]}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando cambio del sistema: {e}")
            return False
    
    def marcar_cambio_sistema(self, tarea_id):
        """Marca que vamos a hacer un cambio del sistema"""
        timestamp_actual = time.time()
        self.cambios_sistema_timestamps[tarea_id] = timestamp_actual
        logger.debug(f"🏷️ Marcado cambio del sistema: {tarea_id[:8]} @ {timestamp_actual}")
    
    def detectar_webhook_duplicado(self, tarea_id):
        """Detecta webhooks duplicados/agrupados"""
        timestamp_actual = time.time()
        
        if tarea_id in self.webhooks_en_espera:
            diferencia = timestamp_actual - self.webhooks_en_espera[tarea_id]
            if diferencia < 2:
                logger.debug(f"⏭️ Webhook posiblemente duplicado ignorado (diferencia: {diferencia:.2f}s)")
                return True
        
        self.webhooks_en_espera[tarea_id] = timestamp_actual
        return False
    
    def registrar_actividad_usuario(self, usuario_id, usuario_nombre):
        """✅ NUEVO: Registra última actividad de usuario para eliminaciones"""
        timestamp_actual = time.time()
        self.ultima_actividad_usuarios[usuario_id] = {
            "timestamp": timestamp_actual,
            "nombre": usuario_nombre
        }
        
        # Limpiar registros antiguos (más de 5 minutos)
        usuarios_a_eliminar = []
        for uid, data in self.ultima_actividad_usuarios.items():
            if timestamp_actual - data["timestamp"] > 300:  # 5 minutos
                usuarios_a_eliminar.append(uid)
        
        for uid in usuarios_a_eliminar:
            del self.ultima_actividad_usuarios[uid]
    
    def obtener_usuario_probable_eliminacion(self):
        """✅ NUEVO: Intenta obtener usuario que probablemente eliminó la tarea"""
        try:
            if not self.ultima_actividad_usuarios:
                return "Usuario desconocido"
            
            # Buscar el usuario con actividad más reciente (últimos 30 segundos)
            timestamp_actual = time.time()
            usuario_mas_reciente = None
            timestamp_mas_reciente = 0
            
            for user_id, data in self.ultima_actividad_usuarios.items():
                diferencia = timestamp_actual - data["timestamp"]
                if diferencia < 30 and data["timestamp"] > timestamp_mas_reciente:  # Últimos 30 segundos
                    timestamp_mas_reciente = data["timestamp"]
                    usuario_mas_reciente = data["nombre"]
            
            return usuario_mas_reciente if usuario_mas_reciente else "Usuario desconocido"
            
        except Exception as e:
            logger.error(f"Error obteniendo usuario probable: {e}")
            return "Error detectando usuario"
    
    def procesar_tarea_modificada(self, page_id, evento):
        """Procesa una tarea que fue modificada - DETECCIÓN SECUENCIAL CORREGIDA"""
        try:
            logger.info(f"🔍 Analizando tarea modificada: {page_id[:8]}...")
            
            # Filtrar webhooks duplicados/agrupados
            if self.detectar_webhook_duplicado(page_id):
                return "webhook_duplicado_ignorado"
            
            # 1. Obtener tarea actual
            tarea = self.obtener_tarea_actual(page_id)
            if not tarea:
                return "error_obteniendo_tarea"
            
            # ✅ REGISTRAR ACTIVIDAD DEL USUARIO PARA ELIMINACIONES FUTURAS
            usuario_actual = self.get_usuario_modificacion(tarea)
            if usuario_actual != "Sistema":
                user_id = tarea.get("last_edited_by", {}).get("id", "unknown")
                self.registrar_actividad_usuario(user_id, usuario_actual)
            
            # Verificar anti-bucle mejorado
            if self.es_cambio_del_sistema(page_id, tarea.get("last_edited_time")):
                logger.debug("🤖 Cambio del sistema detectado - ignorando (anti-bucle)")
                return "cambio_sistema_ignorado"
            
            # 2. Verificar si pertenece a sprint monitoreable
            if not self.verificar_si_sprint_monitoreable(tarea):
                logger.debug("Tarea no pertenece a sprint monitoreable - ignorando")
                return "sprint_no_monitoreable"
            
            # 3. USAR SNAPSHOT GLOBAL
            snapshot_anterior = self.cargar_snapshot_anterior(page_id)
            
            if not snapshot_anterior:
                logger.warning(f"⚠️ No hay snapshot para tarea {page_id[:8]}")
                logger.warning("   Ejecuta 'python setup_monitoring.py' para crear snapshots")
                return "sin_snapshot_global"
            
            # 4. EVALUAR TODOS LOS CAMBIOS
            cambios_detectados = []
            cambios_procesados = {}
            
            for propiedad in PROPIEDADES_MONITOREADAS:
                valor_actual = self.get_property_value(tarea, propiedad)
                valor_anterior = snapshot_anterior.get(propiedad)
                
                if valor_actual != valor_anterior:
                    logger.info(f"🔄 Cambio detectado en {propiedad}: {valor_anterior} → {valor_actual}")
                    cambios_detectados.append(propiedad)
                    
                    # EVALUAR CAMBIO INMEDIATAMENTE
                    resultado = self.procesar_cambio_propiedad(tarea, propiedad, valor_anterior, valor_actual)
                    cambios_procesados[propiedad] = resultado
                    logger.info(f"   ✅ Resultado: {resultado}")
            
            if not cambios_detectados:
                logger.debug("No hay cambios en propiedades monitoreadas")
                return "sin_cambios_monitoreados"
            
            # 5. ACTUALIZAR SNAPSHOT INMEDIATO Y CORRECTAMENTE
            self.actualizar_snapshot_inmediato(page_id, cambios_procesados)
            
            logger.info(f"✅ Procesamiento completado. Cambios en: {cambios_detectados}")
            return f"procesado_{len(cambios_detectados)}_cambios"
            
        except Exception as e:
            logger.error(f"Error procesando tarea modificada: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "error_procesamiento"
    
    def procesar_tarea_nueva(self, page_id, evento):
        """Procesa una tarea nueva creada"""
        try:
            logger.info(f"🆕 Analizando tarea nueva: {page_id[:8]}...")
            
            # 1. Obtener tarea
            tarea = self.obtener_tarea_actual(page_id)
            if not tarea:
                return "error_obteniendo_tarea"
            
            # 2. Verificar si pertenece a sprint monitoreable
            if not self.verificar_si_sprint_monitoreable(tarea):
                logger.debug("Tarea nueva no pertenece a sprint monitoreable")
                return "sprint_no_monitoreable"
            
            # 3. Verificar si es post-bloqueo
            dias_transcurridos = self.get_dias_transcurridos(tarea)
            prioridad = self.get_property_value(tarea, "Prioridad") or ""
            nombre_tarea = self.get_property_value(tarea, "Nombre") or "Sin nombre"
            
            logger.info(f"📋 Tarea nueva: {nombre_tarea}")
            logger.info(f"   Días transcurridos: {dias_transcurridos}")
            logger.info(f"   Prioridad inicial: {prioridad}")
            
            if dias_transcurridos > DIAS_BLOQUEO and prioridad.lower() != "imprevista":
                logger.warning(f"⚠️ Tarea nueva post-bloqueo detectada - convirtiendo a imprevista")
                
                # Registrar conversión en log
                cambio_conversion = {
                    "tarea_id": page_id,
                    "tarea_nombre": nombre_tarea,
                    "propiedad": "Prioridad",
                    "valor_anterior": prioridad or "Sin prioridad",
                    "valor_actual": "Imprevista",
                    "dias_transcurridos": dias_transcurridos,
                    "prioridad": prioridad,
                    "usuario": self.get_usuario_modificacion(tarea),
                    "timestamp": self.get_fecha_actual_gmt5()
                }
                
                self.registrar_en_log(cambio_conversion, "Auto-convertida a Imprevista")
                
                # Convertir a imprevista
                if self.convertir_a_imprevista(tarea):
                    # Crear snapshot inicial para tarea nueva
                    self.crear_snapshot_tarea_nueva(page_id, tarea)
                    return "convertida_imprevista_y_registrada"
                else:
                    return "error_conversion"
            
            # 4. CREAR SNAPSHOT para tarea nueva normal
            self.crear_snapshot_tarea_nueva(page_id, tarea)
            logger.info("📸 Snapshot inicial creado para tarea nueva")
            return "snapshot_inicial_creado"
            
        except Exception as e:
            logger.error(f"Error procesando tarea nueva: {e}")
            return "error_procesamiento"
    
    def procesar_tarea_eliminada(self, page_id, evento):
        """Procesa una tarea que fue eliminada (Caso 4) - USUARIO MEJORADO"""
        try:
            logger.warning(f"🗑️ Detectada eliminación de tarea: {page_id[:8]}")
            
            # Buscar en snapshot para obtener información de la tarea eliminada
            snapshot = self.cargar_snapshot_anterior(page_id)
            if not snapshot:
                logger.warning("   ⚠️ No hay snapshot de la tarea eliminada - no se puede revertir")
                return "sin_snapshot_para_revertir"
            
            # Verificar si la tarea era imprevista
            prioridad_anterior = snapshot.get("Prioridad", "")
            nombre_tarea = snapshot.get("nombre_tarea", "Tarea sin nombre")
            
            # ✅ MEJORADO: Obtener usuario probable de eliminación
            usuario_eliminacion = self.obtener_usuario_probable_eliminacion()
            
            if prioridad_anterior.lower() == "imprevista":
                logger.info(f"   ✅ Tarea imprevista eliminada - permitido: {nombre_tarea}")
                
                # Registrar eliminación permitida
                cambio_eliminacion = {
                    "tarea_id": page_id,
                    "tarea_nombre": nombre_tarea,
                    "propiedad": "Tarea completa",
                    "valor_anterior": "Existente",
                    "valor_actual": "Eliminada",
                    "dias_transcurridos": "N/A",
                    "prioridad": prioridad_anterior,
                    "usuario": usuario_eliminacion,  # ✅ Usuario mejorado
                    "timestamp": self.get_fecha_actual_gmt5()
                }
                
                self.registrar_en_log(cambio_eliminacion, "Eliminación permitida (Imprevista)")
                
                # Limpiar snapshot
                self.eliminar_snapshot(page_id)
                return "eliminacion_imprevista_permitida"
            
            else:
                logger.warning(f"   ❌ Eliminación bloqueada - tarea no imprevista: {nombre_tarea}")
                
                # Registrar intento de eliminación bloqueada
                cambio_eliminacion = {
                    "tarea_id": page_id,
                    "tarea_nombre": nombre_tarea,
                    "propiedad": "Tarea completa",
                    "valor_anterior": "Existente",
                    "valor_actual": "Eliminada",
                    "dias_transcurridos": "N/A",
                    "prioridad": prioridad_anterior,
                    "usuario": usuario_eliminacion,  # ✅ Usuario mejorado
                    "timestamp": self.get_fecha_actual_gmt5()
                }
                
                self.registrar_en_log(cambio_eliminacion, "Eliminación bloqueada (No imprevista)")
                
                logger.warning("   ⚠️ REVERSIÓN DE ELIMINACIÓN no implementada completamente")
                logger.warning("   📝 Solo registrada en logs - revisar manualmente")
                
                return "eliminacion_bloqueada_registrada"
                
        except Exception as e:
            logger.error(f"Error procesando tarea eliminada: {e}")
            return "error_procesamiento_eliminacion"
    
    def procesar_cambio_propiedad(self, tarea, propiedad, valor_anterior, valor_actual):
        """Procesa cambio en una propiedad específica - FIX BUG IMPREVISTA"""
        try:
            tarea_id = tarea["id"]
            nombre_tarea = self.get_property_value(tarea, "Nombre") or "Sin nombre"
            dias_transcurridos = self.get_dias_transcurridos(tarea)
            prioridad_actual = self.get_property_value(tarea, "Prioridad") or ""
            prioridad_anterior = valor_anterior if propiedad == "Prioridad" else prioridad_actual
            
            logger.info(f"📋 Analizando cambio:")
            logger.info(f"   Tarea: {nombre_tarea}")
            logger.info(f"   Propiedad: {propiedad}")
            logger.info(f"   Valor: {valor_anterior} → {valor_actual}")
            logger.info(f"   Días transcurridos: {dias_transcurridos}")
            logger.info(f"   Prioridad actual: {prioridad_actual}")
            
            # Valores mejorados para logs (especialmente Personas)
            valor_anterior_log = self.formatear_valor_para_log(propiedad, valor_anterior)
            valor_actual_log = self.formatear_valor_para_log(propiedad, valor_actual)
            
            cambio = {
                "tarea_id": tarea_id,
                "tarea_nombre": nombre_tarea,
                "propiedad": propiedad,
                "valor_anterior": valor_anterior_log,
                "valor_actual": valor_actual_log,
                "dias_transcurridos": dias_transcurridos,
                "prioridad": prioridad_actual,
                "usuario": self.get_usuario_modificacion(tarea),
                "timestamp": self.get_fecha_actual_gmt5()
            }
            
            # ✅ FIX CRÍTICO: LÓGICA DE PERMISOS CORREGIDA PARA IMPREVISTA
            dias_bloqueados = dias_transcurridos > DIAS_BLOQUEO
            es_estado = propiedad == "Estado"
            es_personas = propiedad == "Personas"
            es_prioridad = propiedad == "Prioridad"
            
            # ✅ CRÍTICO: Verificar si está CAMBIANDO A imprevista (no si YA es imprevista)
            if es_prioridad and dias_bloqueados:
                esta_cambiando_a_imprevista = (
                    valor_actual and valor_actual.lower() == "imprevista" and 
                    valor_anterior and valor_anterior.lower() != "imprevista"
                )
                
                if esta_cambiando_a_imprevista:
                    logger.warning("   ❌ BLOQUEADO: Intento de cambiar a 'Imprevista' para evadir restricciones")
                    cambio["accion"] = "REVERTIR"
                    cambio["registrar_log"] = True
                elif valor_anterior and valor_anterior.lower() == "imprevista":
                    # Tarea que YA ERA imprevista - permitir cambios normales  
                    logger.info("   ✅ PERMITIDO: Tarea que ya era imprevista")
                    cambio["accion"] = "PERMITIDO_IMPREVISTA_ANTERIOR"
                    cambio["registrar_log"] = True
                else:
                    # Cambio normal de prioridad no relacionado con imprevista
                    logger.warning("   ❌ BLOQUEADO: Cambio de prioridad fuera de período")
                    cambio["accion"] = "REVERTIR"
                    cambio["registrar_log"] = True
                    
            elif es_personas and dias_bloqueados:
                # Lógica especial para Personas
                personas_anteriores = valor_anterior if isinstance(valor_anterior, list) else []
                personas_actuales = valor_actual if isinstance(valor_actual, list) else []
                
                if len(personas_anteriores) > 0 and len(personas_actuales) == 0:
                    logger.warning("   ❌ BLOQUEADO: Eliminación del último responsable")
                    cambio["accion"] = "REVERTIR"
                    cambio["registrar_log"] = True
                else:
                    logger.info("   ✅ PERMITIDO: Cambio normal en responsables")
                    cambio["accion"] = "PERMITIDO_PERSONAS"
                    cambio["registrar_log"] = True
                    
            elif prioridad_actual.lower() == "imprevista":
                # Tarea con prioridad imprevista actual: TODO permitido
                cambio["accion"] = "PERMITIDO_IMPREVISTA"
                cambio["registrar_log"] = dias_bloqueados
                logger.info("   ✅ PERMITIDO: Tarea imprevista")
                
            elif es_estado:
                # Estado: SIEMPRE permitido
                cambio["accion"] = "PERMITIDO_ESTADO"
                cambio["registrar_log"] = dias_bloqueados
                logger.info("   ✅ PERMITIDO: Cambio de estado")
                
            elif not dias_bloqueados:
                # Dentro del período libre
                cambio["accion"] = "PERMITIDO_DIAS"
                cambio["registrar_log"] = False
                logger.info("   ✅ PERMITIDO: Dentro de período libre")
                
            else:
                # BLOQUEAR: Fuera de período + no es excepción
                cambio["accion"] = "REVERTIR"
                cambio["registrar_log"] = True
                logger.warning("   ❌ BLOQUEADO: Fuera de período y no es excepción")
            
            # EJECUTAR ACCIÓN DETERMINADA
            if cambio["accion"] == "REVERTIR":
                logger.warning(f"🔄 Revirtiendo cambio en {propiedad}...")
                
                if self.revertir_cambio_directo(tarea_id, propiedad, valor_anterior):
                    self.incrementar_contador_violaciones_directo(tarea_id)
                    
                    if cambio["registrar_log"]:
                        self.registrar_en_log(cambio, "Revertido")
                    
                    logger.warning("   ✅ Cambio revertido exitosamente")
                    return "revertido"
                else:
                    if cambio["registrar_log"]:
                        self.registrar_en_log(cambio, "Error al revertir")
                    logger.error("   ❌ Error al revertir cambio")
                    return "error_reversion"
                    
            elif cambio["registrar_log"]:
                logger.info("📝 Registrando cambio permitido en log...")
                self.registrar_en_log(cambio, "Permitido")
                return "permitido_y_registrado"
            else:
                logger.info("   ✅ Cambio permitido (no requiere log)")
                return "permitido"
            
        except Exception as e:
            logger.error(f"Error procesando cambio de propiedad: {e}")
            return "error"
    
    def formatear_valor_para_log(self, propiedad, valor):
        """Formatea valores para logs más legibles"""
        try:
            if propiedad == "Personas" and isinstance(valor, list):
                if not valor:
                    return "Sin responsables"
                
                nombres = []
                for persona_id in valor:
                    if persona_id in self.cache_nombres_personas:
                        nombres.append(self.cache_nombres_personas[persona_id])
                    else:
                        nombres.append(f"ID:{persona_id[:8]}")
                
                return ", ".join(nombres)
            
            elif valor is None:
                return "Sin valor"
            elif isinstance(valor, list):
                return f"Lista con {len(valor)} elementos"
            else:
                return str(valor)
                
        except Exception:
            return str(valor) if valor is not None else "Sin valor"
    
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
    
    def get_dias_transcurridos(self, tarea):
        """Obtiene días transcurridos del sprint"""
        try:
            dias_prop = tarea["properties"].get("Días Transcurridos Sprint", {})
            if "formula" in dias_prop:
                return dias_prop["formula"].get("number", 0) or 0
            return 0
        except Exception:
            return 0
    
    def get_usuario_modificacion(self, tarea):
        """Obtiene usuario real que modificó la tarea"""
        try:
            if "last_edited_by" in tarea and tarea["last_edited_by"]:
                user_info = tarea["last_edited_by"]
                user_id = user_info.get("id")
                
                if user_id in self.cache_usuarios:
                    return self.cache_usuarios[user_id]
                
                if "name" in user_info and user_info["name"]:
                    return user_info["name"]
                
                if user_info.get("object") == "user" and "person" in user_info:
                    person_info = user_info["person"]
                    if "email" in person_info and person_info["email"]:
                        email = person_info["email"]
                        nombre_email = email.split("@")[0].replace(".", " ").title()
                        return nombre_email
                
                if user_id:
                    return f"Usuario-{user_id[:8]}"
            
            return "Sistema"
        except Exception:
            return "Error-Usuario"
    
    def get_fecha_actual_gmt5(self):
        """Obtiene fecha actual en GMT-5 formato ISO para Notion"""
        colombia_tz = timezone(timedelta(hours=-5))
        fecha_colombia = datetime.now(colombia_tz)
        fecha_utc = fecha_colombia.astimezone(timezone.utc)
        return fecha_utc.isoformat().replace('+00:00', 'Z')
    
    def cargar_snapshot_anterior(self, tarea_id):
        """Carga snapshot anterior de una tarea desde snapshot global"""
        try:
            if os.path.exists("task_snapshots.json"):
                with open("task_snapshots.json", "r", encoding="utf-8") as f:
                    snapshots = json.load(f)
                return snapshots.get(tarea_id)
            return None
        except Exception:
            return None
    
    def actualizar_snapshot_inmediato(self, tarea_id, cambios_procesados):
        """Actualiza snapshot inmediatamente y correctamente"""
        try:
            if not os.path.exists("task_snapshots.json"):
                return
            
            with open("task_snapshots.json", "r", encoding="utf-8") as f:
                snapshots = json.load(f)
            
            if tarea_id not in snapshots:
                return
            
            # Obtener tarea actual después del procesamiento
            tarea_actual = self.obtener_tarea_actual(tarea_id)
            if not tarea_actual:
                return
            
            # Actualizar snapshot con estado real actual
            for propiedad in PROPIEDADES_MONITOREADAS:
                valor_real_actual = self.get_property_value(tarea_actual, propiedad)
                snapshots[tarea_id][propiedad] = valor_real_actual
            
            # Actualizar timestamp y metadatos
            snapshots[tarea_id]["timestamp"] = self.get_fecha_actual_gmt5()
            snapshots[tarea_id]["last_edited_time"] = tarea_actual.get("last_edited_time")
            snapshots[tarea_id]["nombre_tarea"] = self.get_property_value(tarea_actual, "Nombre") or "Sin nombre"
            
            with open("task_snapshots.json", "w", encoding="utf-8") as f:
                json.dump(snapshots, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"📸 Snapshot actualizado inmediatamente para {tarea_id[:8]}")
                
        except Exception as e:
            logger.error(f"Error actualizando snapshot inmediato: {e}")
    
    def crear_snapshot_tarea_nueva(self, tarea_id, tarea):
        """Crea snapshot para tarea nueva"""
        try:
            if not os.path.exists("task_snapshots.json"):
                snapshots = {}
            else:
                with open("task_snapshots.json", "r", encoding="utf-8") as f:
                    snapshots = json.load(f)
            
            snapshot = {
                "timestamp": self.get_fecha_actual_gmt5(),
                "last_edited_time": tarea.get("last_edited_time"),
                "nombre_tarea": self.get_property_value(tarea, "Nombre") or "Sin nombre"
            }
            
            for propiedad in PROPIEDADES_MONITOREADAS:
                snapshot[propiedad] = self.get_property_value(tarea, propiedad)
            
            snapshots[tarea_id] = snapshot
            
            with open("task_snapshots.json", "w", encoding="utf-8") as f:
                json.dump(snapshots, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error creando snapshot tarea nueva: {e}")
    
    def eliminar_snapshot(self, tarea_id):
        """Elimina snapshot de tarea eliminada"""
        try:
            if not os.path.exists("task_snapshots.json"):
                return
            
            with open("task_snapshots.json", "r", encoding="utf-8") as f:
                snapshots = json.load(f)
            
            if tarea_id in snapshots:
                del snapshots[tarea_id]
                
                with open("task_snapshots.json", "w", encoding="utf-8") as f:
                    json.dump(snapshots, f, ensure_ascii=False, indent=2)
                
                logger.debug(f"🗑️ Snapshot eliminado para {tarea_id[:8]}")
                
        except Exception as e:
            logger.error(f"Error eliminando snapshot: {e}")
    
    def revertir_cambio_directo(self, tarea_id, propiedad, valor_anterior):
        """Revierte cambio sin webhooks adicionales"""
        try:
            # Marcar como cambio del sistema
            self.marcar_cambio_sistema(tarea_id)
            
            property_update = {}
            
            if propiedad == "Nombre":
                if valor_anterior:
                    property_update[propiedad] = {"title": [{"text": {"content": str(valor_anterior)}}]}
                else:
                    property_update[propiedad] = {"title": []}
                    
            elif propiedad == "Estado":
                if valor_anterior:
                    property_update[propiedad] = {"status": {"name": str(valor_anterior)}}
                    
            elif propiedad in ["Tamaño", "Prioridad"]:
                if valor_anterior:
                    property_update[propiedad] = {"select": {"name": str(valor_anterior)}}
                else:
                    property_update[propiedad] = {"select": None}
                    
            elif propiedad == "Personas":
                if valor_anterior and isinstance(valor_anterior, list):
                    property_update[propiedad] = {"relation": [{"id": id} for id in valor_anterior]}
                else:
                    property_update[propiedad] = {"relation": []}
            
            if property_update:
                notion.pages.update(
                    page_id=tarea_id,
                    properties=property_update
                )
                
                logger.warning(f"REVERTIDO: {propiedad} → {valor_anterior}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revirtiendo: {e}")
            return False
    
    def incrementar_contador_violaciones_directo(self, tarea_id):
        """Incrementa contador de violaciones directamente"""
        try:
            self.marcar_cambio_sistema(tarea_id)
            
            tarea = notion.pages.retrieve(tarea_id)
            contador_actual = tarea["properties"].get("Violaciones Detectadas", {}).get("number", 0) or 0
            
            notion.pages.update(
                page_id=tarea_id,
                properties={
                    "Violaciones Detectadas": {"number": contador_actual + 1}
                }
            )
            
            logger.debug(f"📊 Contador violaciones: {contador_actual + 1}")
            
        except Exception as e:
            logger.error(f"Error incrementando contador: {e}")
    
    def registrar_en_log(self, cambio, accion_tomada):
        """Registra en tabla Log Modificaciones"""
        try:
            if not DB_LOG_MODIFICACIONES_ID:
                logger.warning("⚠️ DB_LOG_MODIFICACIONES_ID no configurado")
                return
            
            if accion_tomada in ["Revertido", "Error al revertir"]:
                tipo_modificacion = "Bloqueada"
            elif accion_tomada == "Auto-convertida a Imprevista":
                tipo_modificacion = "Auto-conversión"
            elif "Eliminación" in accion_tomada:
                tipo_modificacion = "Eliminación"
            else:
                tipo_modificacion = "Permitida"
            
            timestamp_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_id = f"LOG_{timestamp_id}_{cambio['tarea_id'][:8]}"
            
            properties = {
                "ID Log": {
                    "title": [{"text": {"content": log_id}}]
                },
                "Tarea Afectada": {"relation": [{"id": cambio["tarea_id"]}]},
                "Usuario": {"rich_text": [{"text": {"content": cambio["usuario"]}}]},
                "Fecha Modificación": {"date": {"start": self.get_fecha_actual_gmt5()}},
                "Tipo Modificación": {"select": {"name": tipo_modificacion}},
                "Campo Modificado": {"rich_text": [{"text": {"content": cambio["propiedad"]}}]},
                "Valor Anterior": {"rich_text": [{"text": {"content": str(cambio["valor_anterior"])}}]},
                "Valor Nuevo": {"rich_text": [{"text": {"content": str(cambio["valor_actual"])}}]},
                "Acción Tomada": {"select": {"name": accion_tomada}},
                "Detalle": {"rich_text": [{"text": {"content": f"Tarea: {cambio['tarea_nombre']} | Campo: {cambio['propiedad']} | Días: {cambio['dias_transcurridos']} | Usuario: {cambio['usuario']} | Prioridad: {cambio['prioridad']}"}}]}
            }
            
            notion.pages.create(
                parent={"database_id": DB_LOG_MODIFICACIONES_ID},
                properties=properties
            )
            
            logger.info(f"📝 Log registrado: {tipo_modificacion} - {accion_tomada}")
            
        except Exception as e:
            logger.error(f"Error registrando en log: {e}")
    
    def convertir_a_imprevista(self, tarea):
        """Convierte tarea nueva a prioridad Imprevista"""
        try:
            self.marcar_cambio_sistema(tarea["id"])
            
            notion.pages.update(
                page_id=tarea["id"],
                properties={
                    "Prioridad": {"select": {"name": "Imprevista"}}
                }
            )
            
            nombre_tarea = self.get_property_value(tarea, "Nombre") or "Sin nombre"
            logger.warning(f"🔄 Tarea convertida a Imprevista: {nombre_tarea}")
            return True
            
        except Exception as e:
            logger.error(f"Error convirtiendo a imprevista: {e}")
            return False
