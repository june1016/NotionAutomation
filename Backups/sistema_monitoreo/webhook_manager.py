#!/usr/bin/env python3
"""
Gestor de Webhooks de Notion - Crear/Eliminar webhooks automáticamente
"""

import os
import logging
from notion_client import Client
from dotenv import load_dotenv
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Tu endpoint público

notion = Client(auth=NOTION_TOKEN)

class WebhookManager:
    """Gestor de webhooks de Notion"""
    
    def __init__(self):
        self.webhook_url = WEBHOOK_URL
        
    def crear_webhook_tareas(self):
        """Crea webhook para base de datos de Tareas"""
        try:
            # Crear webhook usando la API de Notion
            webhook_data = {
                "parent": {
                    "type": "database_id",
                    "database_id": DB_TAREAS_ID
                },
                "url": self.webhook_url,
                "event_types": ["page.properties_updated", "page.created"]
            }
            
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            response = requests.post(
                "https://api.notion.com/v1/webhooks",
                json=webhook_data,
                headers=headers
            )
            
            if response.status_code == 200:
                webhook_info = response.json()
                webhook_id = webhook_info["id"]
                logger.info(f"✅ Webhook creado exitosamente: {webhook_id}")
                
                # Guardar ID del webhook para futuras referencias
                with open("webhook_config.txt", "w") as f:
                    f.write(f"WEBHOOK_ID={webhook_id}\n")
                    f.write(f"WEBHOOK_URL={self.webhook_url}\n")
                    
                return webhook_id
            else:
                logger.error(f"Error creando webhook: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error en crear_webhook_tareas: {e}")
            return None
    
    def listar_webhooks(self):
        """Lista todos los webhooks activos"""
        try:
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28"
            }
            
            response = requests.get(
                "https://api.notion.com/v1/webhooks",
                headers=headers
            )
            
            if response.status_code == 200:
                webhooks = response.json()
                logger.info(f"Webhooks activos: {len(webhooks.get('results', []))}")
                for webhook in webhooks.get('results', []):
                    logger.info(f"  - ID: {webhook['id']} | URL: {webhook['url']}")
                return webhooks
            else:
                logger.error(f"Error listando webhooks: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error en listar_webhooks: {e}")
            return None
    
    def eliminar_webhook(self, webhook_id):
        """Elimina un webhook específico"""
        try:
            headers = {
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28"
            }
            
            response = requests.delete(
                f"https://api.notion.com/v1/webhooks/{webhook_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Webhook eliminado: {webhook_id}")
                return True
            else:
                logger.error(f"Error eliminando webhook: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error en eliminar_webhook: {e}")
            return False
    
    def configurar_sistema(self):
        """Configura el sistema completo de webhooks"""
        logger.info("🔧 Configurando sistema de webhooks...")
        
        # 1. Listar webhooks existentes
        self.listar_webhooks()
        
        # 2. Crear webhook para tareas
        webhook_id = self.crear_webhook_tareas()
        
        if webhook_id:
            logger.info("✅ Sistema de webhooks configurado correctamente")
            logger.info(f"🌐 Asegúrate de que tu servidor esté corriendo en: {self.webhook_url}")
        else:
            logger.error("❌ Error configurando webhooks")

def main():
    if not WEBHOOK_URL:
        logger.error("❌ WEBHOOK_URL no configurado en .env")
        logger.info("Ejemplo: WEBHOOK_URL=https://tu-dominio.com/webhook")
        return
    
    manager = WebhookManager()
    manager.configurar_sistema()

if __name__ == "__main__":
    main()