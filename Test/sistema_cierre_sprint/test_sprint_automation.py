"""
Batería Completa de Tests - Automatización de Cierre de Sprint
=============================================================

Suite de testing integral que verifica todos los componentes críticos del sistema
de automatización de cierre de sprint antes de la ejecución en producción.
Incluye tests graduales desde conectividad hasta funcionalidad completa.

COMPONENTES TESTADOS:
1. Conectividad con todas las bases de datos
2. Detección correcta de sprint actual  
3. Obtención y análisis de tareas del sprint
4. Agrupación de tareas por persona
5. Filtrado de tareas para métricas justas
6. Verificación de registros de performance existentes

MODOS DE EJECUCIÓN:
- python test_sprint_automation.py                    # Solo diagnóstico
- python test_sprint_automation.py --ejecutar-performance  # Crear performance
- python test_sprint_automation.py --test-completo         # Test completo + nuevo sprint

CRÍTICO:
Este test debe pasar completamente antes de ejecutar la automatización real.
Cualquier fallo debe investigarse y resolverse antes de proceder.
"""



import os
import sys
import logging
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv

# Agregar el directorio del script principal al path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../Auto/sistema_cierre_sprint'))

# Importar funciones del script principal
from sprint_automation import (
    obtener_sprint_actual, 
    obtener_tareas_del_sprint, 
    agrupar_tareas_por_persona,
    filtrar_tareas_para_metricas,
    obtener_info_persona,
    obtener_area_persona,
    verificar_registro_existente
)

# Configuración de logging para testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [TEST] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_sprint_automation.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_SPRINTS_ID = os.getenv("DB_SPRINTS_ID")
DB_TAREAS_ID = os.getenv("DB_TAREAS_ID") 
DB_PERSONAS_ID = os.getenv("DB_PERSONAS_ID")
DB_PERFORMANCE_ID = os.getenv("DB_PERFORMANCE_ID")

# Inicializar cliente de Notion
notion = Client(auth=NOTION_TOKEN)

def test_1_conexion_bases_datos():
    """Test 1: Verificar conexión con todas las bases de datos"""
    logger.info("🔍 TEST 1: Verificando conexión con bases de datos...")
    
    bases_datos = {
        "Sprints": DB_SPRINTS_ID,
        "Tareas": DB_TAREAS_ID,
        "Personas": DB_PERSONAS_ID,
        "Performance": DB_PERFORMANCE_ID
    }
    
    resultados = {}
    
    for nombre, db_id in bases_datos.items():
        try:
            response = notion.databases.retrieve(db_id)
            resultados[nombre] = "✅ CONEXIÓN OK"
            logger.info(f"  ✅ {nombre}: Conectado correctamente")
        except Exception as e:
            resultados[nombre] = f"❌ ERROR: {e}"
            logger.error(f"  ❌ {nombre}: Error de conexión - {e}")
    
    return resultados

def test_2_sprint_actual():
    """Test 2: Verificar detección del sprint actual"""
    logger.info("🔍 TEST 2: Verificando detección de sprint actual...")
    
    try:
        sprint = obtener_sprint_actual()
        
        if sprint:
            nombre = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
            estado = sprint["properties"]["Estado"]["status"]["name"]
            fecha_inicio = sprint["properties"]["Fecha Inicio"]["date"]["start"]
            fecha_fin = sprint["properties"]["Fecha Fin"]["date"]["start"]
            
            logger.info(f"  ✅ Sprint actual detectado: {nombre}")
            logger.info(f"  📅 Fecha inicio: {fecha_inicio}")
            logger.info(f"  📅 Fecha fin: {fecha_fin}")
            logger.info(f"  📊 Estado: {estado}")
            
            return {
                "status": "✅ SUCCESS",
                "sprint_id": sprint["id"],
                "nombre": nombre,
                "estado": estado,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }
        else:
            logger.error("  ❌ No se detectó ningún sprint actual")
            return {"status": "❌ ERROR", "message": "No hay sprint actual"}
            
    except Exception as e:
        logger.error(f"  ❌ Error al obtener sprint actual: {e}")
        return {"status": "❌ ERROR", "message": str(e)}

def test_3_tareas_sprint(sprint_id):
    """Test 3: Verificar obtención de tareas del sprint"""
    logger.info("🔍 TEST 3: Verificando obtención de tareas del sprint...")
    
    try:
        tareas = obtener_tareas_del_sprint(sprint_id)
        
        logger.info(f"  📊 Total de tareas encontradas: {len(tareas)}")
        
        # Analizar distribución de tareas
        estados = {}
        prioridades = {}
        tareas_problematicas = []
        
        for i, tarea in enumerate(tareas):
            try:
                props = tarea["properties"]
                
                # Contar estados - MANEJO SEGURO DE None
                estado_prop = props.get("Estado") or {}
                status_prop = estado_prop.get("status") or {}
                estado = status_prop.get("name") or "Sin estado"
                estados[estado] = estados.get(estado, 0) + 1
                
                # Contar prioridades - MANEJO SEGURO DE None
                prioridad_prop = props.get("Prioridad") or {}
                select_prop = prioridad_prop.get("select") or {}
                prioridad = select_prop.get("name") or "Sin prioridad"
                prioridades[prioridad] = prioridades.get(prioridad, 0) + 1
                
            except Exception as e:
                # Registrar tareas problemáticas pero continuar
                nombre_tarea = "Sin nombre"
                try:
                    title_prop = props.get("Nombre") or {}
                    title_list = title_prop.get("title") or []
                    if title_list:
                        nombre_tarea = title_list[0].get("text", {}).get("content", "Sin nombre")
                except:
                    pass
                
                tareas_problematicas.append({
                    "indice": i,
                    "nombre": nombre_tarea,
                    "error": str(e)
                })
                
                # Contar como "Error en datos"
                estados["Error en datos"] = estados.get("Error en datos", 0) + 1
                prioridades["Error en datos"] = prioridades.get("Error en datos", 0) + 1
        
        logger.info("  📈 Distribución por estados:")
        for estado, count in estados.items():
            logger.info(f"    - {estado}: {count}")
        
        logger.info("  🎯 Distribución por prioridades:")
        for prioridad, count in prioridades.items():
            logger.info(f"    - {prioridad}: {count}")
        
        if tareas_problematicas:
            logger.warning(f"  ⚠️ Se encontraron {len(tareas_problematicas)} tareas con datos problemáticos:")
            for problema in tareas_problematicas[:5]:  # Mostrar solo las primeras 5
                logger.warning(f"    - Tarea {problema['indice']}: {problema['nombre']} - {problema['error']}")
            if len(tareas_problematicas) > 5:
                logger.warning(f"    ... y {len(tareas_problematicas) - 5} más")
        
        return {
            "status": "✅ SUCCESS",
            "total_tareas": len(tareas),
            "estados": estados,
            "prioridades": prioridades,
            "tareas_problematicas": len(tareas_problematicas),
            "tareas": tareas
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error al obtener tareas: {e}")
        return {"status": "❌ ERROR", "message": str(e)}

def test_4_agrupacion_personas(tareas):
    """Test 4: Verificar agrupación de tareas por persona"""
    logger.info("🔍 TEST 4: Verificando agrupación de tareas por persona...")
    
    try:
        personas, tareas_sin_asignar = agrupar_tareas_por_persona(tareas)
        
        logger.info(f"  👥 Personas con tareas asignadas: {len(personas)}")
        logger.info(f"  ⚠️ Tareas sin asignar: {len(tareas_sin_asignar)}")
        
        # Obtener nombres de personas y estadísticas
        estadisticas_personas = {}
        
        for persona_id, tareas_persona in personas.items():
            try:
                persona_info = obtener_info_persona(persona_id)
                if persona_info:
                    nombre_prop = persona_info["properties"].get("Nombre") or {}
                    title_list = nombre_prop.get("title") or []
                    nombre = title_list[0].get("text", {}).get("content", "Sin nombre") if title_list else "Sin nombre"
                    area = obtener_area_persona(persona_info)
                else:
                    nombre = f"Persona {persona_id[:8]}"
                    area = "Error al obtener"
                
                estadisticas_personas[nombre] = {
                    "id": persona_id,
                    "area": area,
                    "total_tareas": len(tareas_persona),
                    "tareas": tareas_persona
                }
                
                # logger.info(f"    - {nombre} ({area}): {len(tareas_persona)} tareas")
                
                # POR ESTO:
                if area != "Sin departamento asignado":
                    logger.info(f"    - {nombre} ({area}): {len(tareas_persona)} tareas")
                else:
                    logger.info(f"    - {nombre}: {len(tareas_persona)} tareas")  # Sin mostrar área problemática
                
            except Exception as e:
                logger.warning(f"    - Persona {persona_id}: Error al obtener info - {e}")
                # Agregar entrada básica para continuar testing
                estadisticas_personas[f"Persona_{persona_id[:8]}"] = {
                    "id": persona_id,
                    "area": "Error",
                    "total_tareas": len(tareas_persona),
                    "tareas": tareas_persona
                }
        
        return {
            "status": "✅ SUCCESS",
            "total_personas": len(personas),
            "tareas_sin_asignar": len(tareas_sin_asignar),
            "estadisticas": estadisticas_personas
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error en agrupación: {e}")
        return {"status": "❌ ERROR", "message": str(e)}

def test_extra_inspeccion_tareas(tareas):
    """Test EXTRA: Inspección detallada de algunas tareas para diagnóstico"""
    logger.info("🔍 TEST EXTRA: Inspeccionando estructura de tareas...")
    
    try:
        # Inspeccionar las primeras 3 tareas
        for i, tarea in enumerate(tareas[:3]):
            logger.info(f"  📄 TAREA {i+1}:")
            
            try:
                # Mostrar ID
                logger.info(f"    ID: {tarea.get('id', 'Sin ID')}")
                
                # Mostrar propiedades disponibles
                props = tarea.get("properties", {})
                logger.info(f"    Propiedades disponibles: {list(props.keys())}")
                
                # Inspeccionar propiedades críticas
                propiedades_criticas = ["Nombre", "Estado", "Prioridad", "Carga", "Carga Completada", "Completada"]
                
                for prop_name in propiedades_criticas:
                    prop_value = props.get(prop_name)
                    if prop_value is None:
                        logger.info(f"    {prop_name}: None")
                    elif isinstance(prop_value, dict):
                        logger.info(f"    {prop_name}: {type(prop_value).__name__} - Keys: {list(prop_value.keys())}")
                        # Mostrar valor específico si es simple
                        if len(str(prop_value)) < 100:
                            logger.info(f"      Valor: {prop_value}")
                    else:
                        logger.info(f"    {prop_name}: {type(prop_value).__name__} - {prop_value}")
                
            except Exception as e:
                logger.error(f"    ❌ Error inspeccionando tarea {i+1}: {e}")
        
        return {"status": "✅ SUCCESS", "message": "Inspección completada"}
        
    except Exception as e:
        logger.error(f"  ❌ Error en inspección: {e}")
        return {"status": "❌ ERROR", "message": str(e)}

def test_5_filtrado_metricas(estadisticas_personas):
    """Test 5: Verificar filtrado de tareas para métricas"""
    logger.info("🔍 TEST 5: Verificando filtrado de tareas para métricas...")
    
    try:
        resultados_filtrado = {}
        
        for nombre, data in estadisticas_personas.items():
            try:
                tareas_persona = data["tareas"]
                
                # Aplicar filtrado
                tareas_para_metricas, tareas_excluidas, stats = filtrar_tareas_para_metricas(tareas_persona)
                
                resultados_filtrado[nombre] = {
                    "total_original": stats["total_original"],
                    "para_metricas": stats["total_para_metricas"],
                    "excluidas": stats["total_excluidas"],
                    "imprevistas_completadas": stats["imprevistas_completadas_incluidas"]
                }
                
                logger.info(f"  👤 {nombre}:")
                logger.info(f"    - Original: {stats['total_original']}")
                logger.info(f"    - Para métricas: {stats['total_para_metricas']}")
                logger.info(f"    - Excluidas: {stats['total_excluidas']}")
                logger.info(f"    - Imprevistas completadas: {stats['imprevistas_completadas_incluidas']}")
                
                if tareas_excluidas:
                    logger.info(f"    - Tareas excluidas:")
                    for excluida in tareas_excluidas[:3]:  # Mostrar solo las primeras 3
                        logger.info(f"      * {excluida['nombre']} ({excluida['razon']})")
                    if len(tareas_excluidas) > 3:
                        logger.info(f"      ... y {len(tareas_excluidas) - 3} más")
                        
            except Exception as e:
                logger.error(f"    ❌ Error al procesar {nombre}: {e}")
                resultados_filtrado[nombre] = {
                    "error": str(e)
                }
        
        return {
            "status": "✅ SUCCESS",
            "resultados": resultados_filtrado
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error en filtrado: {e}")
        return {"status": "❌ ERROR", "message": str(e)}

def test_6_verificar_performance_existente(estadisticas_personas, sprint_id):
    """Test 6: Verificar si ya existen registros de performance"""
    logger.info("🔍 TEST 6: Verificando registros de performance existentes...")
    
    try:
        registros_existentes = {}
        
        for nombre, data in estadisticas_personas.items():
            persona_id = data["id"]
            existe = verificar_registro_existente(persona_id, sprint_id)
            
            registros_existentes[nombre] = existe
            
            if existe:
                logger.warning(f"  ⚠️ {nombre}: YA TIENE registro de performance")
            else:
                logger.info(f"  ✅ {nombre}: Sin registro previo")
        
        return {
            "status": "✅ SUCCESS",
            "registros_existentes": registros_existentes
        }
        
    except Exception as e:
        logger.error(f"  ❌ Error al verificar performance: {e}")
        return {"status": "❌ ERROR", "message": str(e)}

def ejecutar_tests_completos():
    """Ejecuta todos los tests en secuencia"""
    logger.info("🚀 INICIANDO BATERÍA COMPLETA DE TESTS")
    logger.info("=" * 60)
    
    resultados = {}
    
    # Test 1: Conexión
    resultados["test_1"] = test_1_conexion_bases_datos()
    
    # Test 2: Sprint actual
    resultado_sprint = test_2_sprint_actual()
    resultados["test_2"] = resultado_sprint
    
    if resultado_sprint["status"] == "✅ SUCCESS":
        sprint_id = resultado_sprint["sprint_id"]
        
        # Test 3: Tareas
        resultado_tareas = test_3_tareas_sprint(sprint_id)
        resultados["test_3"] = resultado_tareas
        
        if resultado_tareas["status"] == "✅ SUCCESS":
            tareas = resultado_tareas["tareas"]
            
            # Test EXTRA: Inspección detallada
            resultados["test_extra"] = test_extra_inspeccion_tareas(tareas)
            
            # Test 4: Agrupación
            resultado_agrupacion = test_4_agrupacion_personas(tareas)
            resultados["test_4"] = resultado_agrupacion
            
            if resultado_agrupacion["status"] == "✅ SUCCESS":
                estadisticas = resultado_agrupacion["estadisticas"]
                
                # Test 5: Filtrado
                resultados["test_5"] = test_5_filtrado_metricas(estadisticas)
                
                # Test 6: Performance existente
                resultados["test_6"] = test_6_verificar_performance_existente(estadisticas, sprint_id)
    
    # Resumen final
    logger.info("=" * 60)
    logger.info("📋 RESUMEN DE TESTS:")
    
    for test_name, resultado in resultados.items():
        if isinstance(resultado, dict) and "status" in resultado:
            logger.info(f"  {test_name}: {resultado['status']}")
        else:
            logger.info(f"  {test_name}: {resultado}")
    
    return resultados

def mostrar_instrucciones_siguientes():
    """Muestra instrucciones para el siguiente paso"""
    logger.info("=" * 60)
    logger.info("📝 PRÓXIMOS PASOS RECOMENDADOS:")
    logger.info("")
    logger.info("1. Si todos los tests pasaron ✅:")
    logger.info("   - Ejecutar: python test_sprint_automation.py --ejecutar-performance")
    logger.info("   - Esto creará los registros de performance SOLO")
    logger.info("")
    logger.info("2. Si hay registros existentes:")
    logger.info("   - Limpiar tabla Performance manualmente")
    logger.info("   - Volver a ejecutar tests")
    logger.info("")
    logger.info("3. Para test completo (incluye crear Sprint 81):")
    logger.info("   - Ejecutar: python test_sprint_automation.py --test-completo")
    logger.info("")
    logger.info("⚠️  IMPORTANTE: Este es entorno de PRUEBAS")
    logger.info("   Revisa logs detallados en: test_sprint_automation.log")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--ejecutar-performance":
            # Ejecutar solo creación de performance
            from sprint_automation import ejecutar_cierre_sprint
            logger.info("🔥 EJECUTANDO CREACIÓN DE PERFORMANCE...")
            resultado = ejecutar_cierre_sprint()
            if resultado:
                logger.info("✅ Performance creado exitosamente")
            else:
                logger.error("❌ Error al crear performance")
                
        elif sys.argv[1] == "--test-completo":
            # Test completo incluyendo creación de sprint
            logger.info("🔥 EJECUTANDO TEST COMPLETO...")
            ejecutar_tests_completos()
            
            from sprint_automation import ejecutar_cierre_sprint
            resultado = ejecutar_cierre_sprint()
            if resultado:
                logger.info("✅ TEST COMPLETO EXITOSO")
            else:
                logger.error("❌ TEST COMPLETO FALLÓ")
        else:
            logger.error("❌ Argumento no reconocido")
    else:
        # Solo ejecutar tests de diagnóstico
        ejecutar_tests_completos()
        mostrar_instrucciones_siguientes()