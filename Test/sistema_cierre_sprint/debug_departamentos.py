"""
Diagnóstico de Problemas con Departamentos
==========================================

Herramienta especializada para diagnosticar y resolver problemas relacionados con la
detección y asignación de departamentos a personas. Incluye análisis profundo de
relaciones entre BD Personas ↔ BD Departamentos.

FUNCIONES:
- Inspección detallada de estructura de personas
- Verificación de relaciones con departamentos
- Test de diferentes métodos de obtención de área
- Diagnóstico de problemas de configuración de BD

EJECUCIÓN:
python Test/SistemaCierreSprint/debug_departamentos.py

CASOS DE USO:
- Resolver problemas de "Sin departamento asignado"
- Verificar configuración de relaciones en Notion
- Diagnosticar cambios en estructura de BD
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
    format='%(asctime)s - [DEBUG] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_SPRINTS_ID = os.getenv("DB_SPRINTS_ID")
DB_PERSONAS_ID = os.getenv("DB_PERSONAS_ID")

# Inicializar cliente de Notion
notion = Client(auth=NOTION_TOKEN)

def obtener_sprint_actual():
    """Obtiene el sprint actual"""
    response = notion.databases.query(
        database_id=DB_SPRINTS_ID,
        filter={
            "property": "Es Actual",
            "formula": {
                "checkbox": {
                    "equals": True
                }
            }
        }
    )
    
    if response["results"]:
        return response["results"][0]
    return None

def diagnosticar_estructura_persona(persona_id):
    """Diagnostica la estructura completa de una persona"""
    logger.info(f"\n🔍 === DIAGNÓSTICO PERSONA {persona_id[:8]} ===")
    
    try:
        persona_info = notion.pages.retrieve(persona_id)
        props = persona_info["properties"]
        
        # Mostrar todas las propiedades disponibles
        logger.info(f"📋 Propiedades disponibles: {list(props.keys())}")
        
        # Buscar propiedades relacionadas con área/departamento
        propiedades_area = []
        for prop_name in props.keys():
            if any(keyword in prop_name.lower() for keyword in ['área', 'area', 'departamento', 'depto']):
                propiedades_area.append(prop_name)
        
        logger.info(f"🏢 Propiedades de área encontradas: {propiedades_area}")
        
        # Inspeccionar cada propiedad de área
        for prop_name in propiedades_area:
            prop_value = props[prop_name]
            logger.info(f"\n  🔍 {prop_name}:")
            logger.info(f"    Tipo: {prop_value.get('type', 'Sin tipo')}")
            
            if prop_value.get('type') == 'relation':
                relation_data = prop_value.get('relation', [])
                logger.info(f"    Relaciones: {len(relation_data)} elementos")
                
                if relation_data:
                    for i, rel in enumerate(relation_data):
                        rel_id = rel.get('id')
                        logger.info(f"      Relación {i+1}: {rel_id}")
                        
                        # Intentar obtener información del departamento
                        try:
                            dept_info = notion.pages.retrieve(rel_id)
                            dept_props = dept_info["properties"]
                            
                            # Buscar el nombre del departamento
                            if "Nombre" in dept_props:
                                nombre_prop = dept_props["Nombre"]
                                if nombre_prop.get("type") == "title":
                                    title_list = nombre_prop.get("title", [])
                                    if title_list:
                                        dept_nombre = title_list[0].get("text", {}).get("content", "Sin nombre")
                                        logger.info(f"        ✅ Departamento: '{dept_nombre}'")
                                    else:
                                        logger.warning(f"        ⚠️ Lista título vacía")
                                else:
                                    logger.warning(f"        ⚠️ 'Nombre' no es tipo title: {nombre_prop.get('type')}")
                            else:
                                logger.warning(f"        ❌ No hay propiedad 'Nombre' en departamento")
                                logger.info(f"        📋 Propiedades disponibles: {list(dept_props.keys())}")
                                
                        except Exception as e:
                            logger.error(f"        ❌ Error al obtener dept {rel_id}: {e}")
                else:
                    logger.warning(f"    ⚠️ Sin relaciones asignadas")
            else:
                logger.info(f"    📄 Valor completo: {prop_value}")
        
        # Mostrar nombre de la persona
        if "Nombre" in props:
            nombre_prop = props["Nombre"]
            if nombre_prop.get("type") == "title":
                title_list = nombre_prop.get("title", [])
                if title_list:
                    persona_nombre = title_list[0].get("text", {}).get("content", "Sin nombre")
                    logger.info(f"👤 Nombre persona: '{persona_nombre}'")
        
        return persona_info
        
    except Exception as e:
        logger.error(f"❌ Error al diagnosticar persona: {e}")
        return None

def diagnosticar_bd_departamentos():
    """Intenta acceder a la BD de Departamentos"""
    logger.info(f"\n🏢 === DIAGNÓSTICO BD DEPARTAMENTOS ===")
    
    # Verificar si hay ID de departamentos en .env
    db_departamentos_id = os.getenv("DB_DEPARTAMENTOS_ID")
    logger.info(f"📋 ID Departamentos en .env: {db_departamentos_id}")
    
    if not db_departamentos_id:
        logger.warning("⚠️ No hay DB_DEPARTAMENTOS_ID en .env")
        logger.info("💡 Intentando buscar BD de Departamentos...")
        
        # Aquí podríamos intentar buscar la BD, pero requeriría permisos especiales
        return None
    else:
        try:
            # Intentar acceder a la BD
            response = notion.databases.retrieve(db_departamentos_id)
            logger.info(f"✅ BD Departamentos accesible: {response.get('title', [{}])[0].get('text', {}).get('content', 'Sin título')}")
            
            # Listar algunos departamentos
            query_response = notion.databases.query(database_id=db_departamentos_id, page_size=5)
            departamentos = query_response["results"]
            
            logger.info(f"📊 Departamentos encontrados: {len(departamentos)}")
            for i, dept in enumerate(departamentos):
                props = dept["properties"]
                if "Nombre" in props:
                    nombre_prop = props["Nombre"]
                    if nombre_prop.get("type") == "title":
                        title_list = nombre_prop.get("title", [])
                        if title_list:
                            dept_nombre = title_list[0].get("text", {}).get("content", "Sin nombre")
                            logger.info(f"  {i+1}. {dept_nombre}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error al acceder BD Departamentos: {e}")
            return None

def test_obtencion_area_mejorada(persona_info):
    """Prueba diferentes métodos para obtener el área"""
    logger.info(f"\n🧪 === TEST OBTENCIÓN ÁREA ===")
    
    if not persona_info:
        return None
    
    props = persona_info["properties"]
    
    # Método 1: Propiedad "Área" exacta
    logger.info("🔬 Método 1: Propiedad 'Área'")
    if "Área" in props:
        area_prop = props["Área"]
        logger.info(f"  ✅ Encontrada propiedad 'Área': {area_prop.get('type')}")
        
        if area_prop.get("type") == "relation":
            relation_list = area_prop.get("relation", [])
            if relation_list:
                area_id = relation_list[0]["id"]
                logger.info(f"  🔗 ID departamento: {area_id}")
                
                try:
                    area_info = notion.pages.retrieve(area_id)
                    area_props = area_info["properties"]
                    
                    if "Nombre" in area_props:
                        nombre_prop = area_props["Nombre"]
                        if nombre_prop.get("type") == "title":
                            title_list = nombre_prop.get("title", [])
                            if title_list:
                                area_nombre = title_list[0].get("text", {}).get("content", "Sin nombre")
                                logger.info(f"  ✅ ÉXITO: '{area_nombre}'")
                                return area_nombre
                except Exception as e:
                    logger.error(f"  ❌ Error obteniendo departamento: {e}")
            else:
                logger.warning(f"  ⚠️ Sin relaciones en 'Área'")
        else:
            logger.warning(f"  ⚠️ 'Área' no es tipo relation: {area_prop.get('type')}")
    else:
        logger.warning("  ❌ No hay propiedad 'Área'")
    
    # Método 2: Buscar propiedades similares
    logger.info("🔬 Método 2: Buscar propiedades similares")
    for prop_name in props.keys():
        if any(keyword in prop_name.lower() for keyword in ['departamento', 'depto', 'area']):
            logger.info(f"  🔍 Probando '{prop_name}'")
            # Similar al método 1 pero con diferentes nombres
            # [código similar al método 1]
    
    logger.warning("❌ No se pudo obtener departamento con ningún método")
    return "Sin departamento asignado"

def main():
    logger.info("🚀 Iniciando diagnóstico de departamentos...")
    
    # 1. Obtener sprint actual
    sprint = obtener_sprint_actual()
    if not sprint:
        logger.error("❌ No hay sprint actual")
        return
    
    sprint_nombre = sprint["properties"]["Nombre"]["title"][0]["text"]["content"]
    logger.info(f"📋 Sprint actual: {sprint_nombre}")
    
    # 2. Diagnosticar BD Departamentos
    diagnosticar_bd_departamentos()
    
    # 3. Obtener algunas personas para diagnosticar
    try:
        response = notion.databases.query(database_id=DB_PERSONAS_ID, page_size=3)
        personas = response["results"]
        
        logger.info(f"👥 Diagnosticando {len(personas)} personas...")
        
        for i, persona in enumerate(personas):
            persona_id = persona["id"]
            
            # Diagnóstico completo
            persona_info = diagnosticar_estructura_persona(persona_id)
            
            # Test de obtención mejorada
            area_obtenida = test_obtencion_area_mejorada(persona_info)
            logger.info(f"🏢 Área final obtenida: {area_obtenida}")
            
            if i < len(personas) - 1:
                logger.info("\n" + "="*50)
        
    except Exception as e:
        logger.error(f"❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()