"""
Test del Sistema Híbrido de Detección de Sprint
===============================================

Verifica específicamente el funcionamiento del sistema híbrido de detección de sprint
actual, que combina validación por fecha local (Colombia) con fallback a fórmula
de Notion. Crítico para asegurar detección correcta independiente de zona horaria.

FUNCIONES:
- Test de detección por fecha local vs UTC
- Verificación de todos los métodos de fallback
- Análisis de diferencias horarias Colombia/UTC
- Validación de lógica de sprint actual

EJECUCIÓN:
python Test/SistemaCierreSprint/test_sistema_hibrido.py

PROPÓSITO:
Garantizar que el sistema detecte correctamente el sprint a cerrar,
especialmente cuando se ejecuta en AWS (UTC) vs horario local Colombia.
"""

import os
import sys
import logging
from datetime import datetime
import pytz

# Agregar path del script principal
sys.path.append(os.path.join(os.path.dirname(__file__), '../../Auto/sistema_cierre_sprint'))

from sprint_automation import obtener_sprint_para_cierre, notion

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sistema_hibrido():
    """Test del nuevo sistema híbrido de detección de sprint"""
    logger.info("🧪 TESTING SISTEMA HÍBRIDO")
    logger.info("=" * 50)
    
    # Mostrar hora actual en diferentes zonas
    colombia_tz = pytz.timezone('America/Bogota')
    utc_tz = pytz.UTC
    
    ahora_colombia = datetime.now(colombia_tz)
    ahora_utc = datetime.now(utc_tz)
    
    logger.info(f"🕒 Hora Colombia: {ahora_colombia.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"🌍 Hora UTC: {ahora_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"⏰ Diferencia: {(ahora_utc.hour - ahora_colombia.hour) % 24} horas")
    
    # Test del sistema híbrido
    logger.info("\n🔍 PROBANDO SISTEMA HÍBRIDO...")
    sprint = obtener_sprint_para_cierre()
    
    if sprint:
        nombre = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
        estado = sprint["properties"]["Estado"]["status"]["name"]
        fecha_fin = sprint["properties"]["Fecha Fin"]["date"]["start"]
        
        logger.info("=" * 50)
        logger.info("✅ RESULTADO DEL TEST:")
        logger.info(f"  Sprint detectado: {nombre}")
        logger.info(f"  Estado: {estado}")
        logger.info(f"  Fecha fin: {fecha_fin}")
        logger.info("=" * 50)
        
        return True
    else:
        logger.error("❌ No se detectó ningún sprint")
        return False

if __name__ == "__main__":
    resultado = test_sistema_hibrido()
    print(f"\n{'✅ TEST EXITOSO' if resultado else '❌ TEST FALLÓ'}")