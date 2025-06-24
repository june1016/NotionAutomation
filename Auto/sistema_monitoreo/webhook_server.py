#!/usr/bin/env python3
"""
Servidor de Webhooks - CON SOPORTE PARA CASO 4 (Eliminación de tareas)
Includes: Detección de eliminación + Logging mejorado + Anti-duplicados
"""

import os
import logging
import json
import hmac
import hashlib
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from task_monitor import TaskMonitorReactivo
import threading
from queue import Queue
import time

# Configuración de logging mejorada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook_server.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID")

app = Flask(__name__)

# Queue para procesar eventos de forma asíncrona
event_queue = Queue()
monitor = TaskMonitorReactivo()

class WebhookProcessor:
    """Procesador de eventos de webhook - CON SOPORTE CASO 4"""
    
    def __init__(self):
        self.processing = True
        self.eventos_procesados = 0
        self.eventos_ignorados = 0
        self.eventos_duplicados = 0  # ✅ NUEVO: Tracking de duplicados
        
    def verificar_webhook_signature(self, request_body, signature):
        """Verifica la autenticidad del webhook"""
        if not WEBHOOK_SECRET:
            return True  # Para desarrollo sin secret
        
        try:
            expected_signature = hmac.new(
                WEBHOOK_SECRET.encode(),
                request_body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except Exception as e:
            logger.error(f"Error verificando signature: {e}")
            return False
    
    def procesar_evento_tarea(self, evento):
        """Procesa evento específico de tarea - CON SOPORTE ELIMINACIÓN"""
        try:
            event_type = evento.get("type")
            page_id = evento.get("page_id")
            
            if not page_id:
                logger.error(f"❌ No se pudo obtener page_id del evento")
                return
            
            logger.info(f"📝 Procesando evento: {event_type} | Página: {page_id[:8]}...")
            
            if event_type == "page.properties_updated":
                # Tarea modificada
                resultado = monitor.procesar_tarea_modificada(page_id, evento)
                
                if resultado == "webhook_duplicado_ignorado":
                    self.eventos_duplicados += 1
                    logger.debug(f"⏭️ Webhook duplicado ignorado")
                else:
                    self.eventos_procesados += 1
                    logger.info(f"✅ Resultado modificación: {resultado}")
                
            elif event_type == "page.created":
                # Tarea nueva
                resultado = monitor.procesar_tarea_nueva(page_id, evento)
                self.eventos_procesados += 1
                logger.info(f"✅ Resultado nueva tarea: {resultado}")
                
            elif event_type == "page.deleted":
                # ✅ NUEVO: Tarea eliminada (Caso 4)
                resultado = monitor.procesar_tarea_eliminada(page_id, evento)
                self.eventos_procesados += 1
                logger.warning(f"🗑️ Resultado eliminación: {resultado}")
                
        except Exception as e:
            logger.error(f"❌ Error procesando evento: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def worker_eventos(self):
        """Worker que procesa eventos de la queue - MEJORADO"""
        logger.info("🔄 Worker de eventos iniciado")
        
        while self.processing:
            try:
                if not event_queue.empty():
                    evento = event_queue.get(timeout=1)
                    self.procesar_evento_tarea(evento)
                    event_queue.task_done()
                else:
                    time.sleep(0.1)  # Esperar si no hay eventos
                    
            except Exception as e:
                logger.error(f"Error en worker: {e}")
                time.sleep(1)

# Instancia global del procesador
processor = WebhookProcessor()

@app.route('/webhook', methods=['POST', 'GET'])
def webhook_endpoint():
    """Endpoint principal - CON SOPORTE PARA ELIMINACIÓN"""
    try:
        if request.method == 'POST':
            evento_data = request.get_json()
            
            # MANEJAR TOKEN DE VERIFICACIÓN
            if evento_data and 'verification_token' in evento_data:
                verification_token = evento_data.get('verification_token')
                print(verification_token)
                logger.info("🔐 TOKEN DE VERIFICACIÓN RECIBIDO")
                return jsonify({"verification_token": verification_token}), 200
            
            if not evento_data:
                logger.warning("❌ Datos de webhook vacíos")
                return jsonify({"error": "No data"}), 400
            
            # 🚨 FILTRAR WEBHOOKS DEL PROPIO SISTEMA (ANTI-BUCLE)
            authors = evento_data.get("authors", [])
            integration_id = evento_data.get("integration_id")
            
            for author in authors:
                if author.get("type") == "bot" or author.get("id") == integration_id:
                    logger.debug("🤖 WEBHOOK DEL SISTEMA IGNORADO (anti-bucle)")
                    return jsonify({"status": "ignored_system"}), 200
            
            event_type = evento_data.get('type', 'unknown')
            
            # ✅ EVENTOS RELEVANTES AMPLIADOS (incluye eliminación)
            eventos_relevantes = ['page.properties_updated', 'page.created', 'page.deleted']
            
            if event_type not in eventos_relevantes:
                logger.debug(f"⏭️ Evento ignorado (irrelevante): {event_type}")
                processor.eventos_ignorados += 1
                return jsonify({"status": "ignored_irrelevant"}), 200
            
            # OBTENER INFORMACIÓN DE LA ESTRUCTURA NOTION
            entity = evento_data.get("entity", {})
            data = evento_data.get("data", {})
            
            # Extraer page_id
            page_id = entity.get("id")
            if not page_id:
                logger.error("❌ No se encontró page_id en entity")
                return jsonify({"error": "No page_id"}), 400
            
            # ✅ FILTRO CRÍTICO: Solo procesar DB_TAREAS
            parent = data.get("parent", {})
            database_id = parent.get("id")
            
            # ✅ CASO ESPECIAL: page.deleted puede no tener parent en data
            if event_type == "page.deleted":
                # Para eventos de eliminación, asumimos que es relevante si llegó hasta aquí
                # Ya que el filtro anti-bucle ya funcionó
                logger.debug(f"🗑️ Evento de eliminación procesado sin verificar DB (limitación de Notion)")
            elif database_id != DB_TAREAS_ID:
                logger.debug(f"⏭️ Database no relevante ignorada: {database_id[:8] if database_id else 'unknown'}...")
                processor.eventos_ignorados += 1
                return jsonify({"status": "different_database"}), 200
            
            # ✅ SI LLEGAMOS AQUÍ: Es evento relevante
            logger.info(f"🎯 Evento VÁLIDO: {event_type} | Página: {page_id[:8]}...")
            
            # Agregar propiedades cambiadas si están disponibles
            if "updated_properties" in data:
                evento_data["properties"] = data["updated_properties"]
                logger.debug(f"📝 Propiedades cambiadas: {len(data['updated_properties'])}")
            
            # Agregar page_id para compatibilidad
            evento_data["page_id"] = page_id
            
            # Agregar a queue para procesamiento
            event_queue.put(evento_data)
            logger.info("✅ Evento agregado a queue para procesamiento")
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        logger.error(f"❌ Error en webhook endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal error"}), 500

@app.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    """Endpoint para pruebas - MEJORADO"""
    return jsonify({
        "message": "Servidor webhook funcionando correctamente",
        "version": "v2.0 - Con soporte eliminación",
        "configuracion": {
            "db_tareas_monitoreada": DB_TAREAS_ID[:8] + "..." if DB_TAREAS_ID else "No configurada",
            "eventos_procesados": processor.eventos_procesados,
            "eventos_ignorados": processor.eventos_ignorados,
            "eventos_duplicados": processor.eventos_duplicados
        }
    }), 200

@app.route('/status', methods=['GET'])
def status_endpoint():
    """Endpoint para verificar estado del servidor - COMPLETO"""
    return jsonify({
        "status": "running",
        "version": "v2.0",
        "eventos_pendientes": event_queue.qsize(),
        "monitor_activo": processor.processing,
        "estadisticas": {
            "eventos_procesados": processor.eventos_procesados,
            "eventos_ignorados": processor.eventos_ignorados,
            "eventos_duplicados": processor.eventos_duplicados,
            "cache_usuarios": len(monitor.cache_usuarios),
            "cache_nombres_personas": len(monitor.cache_nombres_personas)
        },
        "configuracion": {
            "db_tareas_id": DB_TAREAS_ID[:8] + "..." if DB_TAREAS_ID else "No configurada",
            "zona_horaria": "GMT-5 (Colombia)",
            "eventos_soportados": ["page.properties_updated", "page.created", "page.deleted"]
        }
    }), 200

@app.route('/debug', methods=['POST'])
def debug_endpoint():
    """Endpoint para debug de webhooks - MEJORADO"""
    try:
        data = request.get_json()
        headers = dict(request.headers)
        
        logger.info("=== DEBUG WEBHOOK ===")
        logger.info(f"Headers: {headers}")
        logger.info(f"Event Type: {data.get('type', 'unknown')}")
        logger.info(f"Entity: {data.get('entity', {})}")
        logger.info(f"Authors: {data.get('authors', [])}")
        logger.info(f"Data Parent: {data.get('data', {}).get('parent', {})}")
        logger.info("=== END DEBUG ===")
        
        return jsonify({
            "debug": "received", 
            "event_type": data.get('type'),
            "entity_id": data.get('entity', {}).get('id'),
            "database_id": data.get('data', {}).get('parent', {}).get('id'),
            "esperada_db": DB_TAREAS_ID,
            "eventos_soportados": ["page.properties_updated", "page.created", "page.deleted"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error en debug: {e}")
        return jsonify({"error": str(e)}), 500

def iniciar_worker():
    """Inicia el worker de procesamiento en thread separado"""
    worker_thread = threading.Thread(target=processor.worker_eventos, daemon=True)
    worker_thread.start()
    logger.info("🚀 Worker de eventos iniciado en thread separado")

if __name__ == '__main__':
    logger.info("🌐 Iniciando servidor de webhooks v2.0...")
    
    # Verificar configuración crítica
    if not NOTION_TOKEN:
        logger.error("❌ NOTION_TOKEN no configurado")
        exit(1)
    
    if not DB_TAREAS_ID:
        logger.error("❌ DB_TAREAS_ID no configurado")
        exit(1)
    
    logger.info(f"📋 Monitoreando DB de Tareas: {DB_TAREAS_ID[:8]}...")
    logger.info("🗑️ Soporte para eliminación de tareas: ACTIVADO")
    
    # Inicializar monitor
    monitor.inicializar()
    
    # Iniciar worker de procesamiento
    iniciar_worker()
    
    # Iniciar servidor Flask
    port = int(os.getenv("WEBHOOK_PORT", 5000))
    logger.info(f"🚀 Servidor v2.0 iniciado en puerto {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,  # No debug en producción
        threaded=True
    )